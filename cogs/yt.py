from datetime import datetime, timezone
import logging
import re

import discord
from discord.ext import commands, tasks

from api.yt_api import YoutubeAPI
from utils import YT_COLOR, MAX_EMBED_LIMIT, DB

logger = logging.getLogger('bot')


class Youtube(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.yt_api = YoutubeAPI()
        self.db = DB().create_db()
        self.update_new_video.start()
        self.update_channel_info.start()
        
    async def cog_unload(self):
        self.update_new_video.cancel()
        self.update_channel_info.cancel()
    
    def __duration_transfer(self, duration: str) -> str:
        """
        input: ISO 8601 format string(like "P2DT2H1S", "PT1M46S"), but datetime not support, 
               so we need to handle it ourselves.
        output ex: "50:00:01", "00:01:46"
        """
        days_pattern = re.compile(r'(\d+)D')
        hours_pattern = re.compile(r'(\d+)H')
        minutes_pattern = re.compile(r'(\d+)M')
        seconds_pattern = re.compile(r'(\d+)S')

        days = days_pattern.search(duration)
        hours = hours_pattern.search(duration)
        minutes = minutes_pattern.search(duration)
        seconds = seconds_pattern.search(duration)

        days = int(days.group(1)) if days else 0
        hours = int(hours.group(1)) if hours else 0
        hours += days * 24
        minutes = int(minutes.group(1)) if minutes else 0
        seconds = int(seconds.group(1)) if seconds else 0

        time = [str(val).rjust(2, '0') for val in (hours, minutes, seconds)]

        return ':'.join(time)
    
    def __isoformat_transfer(self, video_info: dict, paths: str) -> str:
        video_info_time = self.yt_api.analyze_data(video_info, paths)
        time = datetime.fromisoformat(video_info_time)
        delta = time - datetime(1970, 1, 1, tzinfo=time.tzinfo)
        # discord timestamp(ex: 2024年1月8日星期一 16:23)
        return f"<t:{int(delta.total_seconds())}:F>, <t:{int(delta.total_seconds())}:R>"
    
    def __create_embed(self, video_info: dict, channel_icon_url: str) -> discord.Embed:
        video_id = self.yt_api.analyze_data(video_info, ['id'])
        video_title = self.yt_api.analyze_data(video_info, ['snippet', 'title'])
        video_thumbnail_url = self.yt_api.analyze_data(video_info, ['snippet', 'thumbnails', 'standard', 'url'])
        channel_id = self.yt_api.analyze_data(video_info, ['snippet', 'channelId'])
        channel_title = self.yt_api.analyze_data(video_info, ['snippet', 'channelTitle'])
        
        # create embed
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        channel_url = f'https://www.youtube.com/channel/{channel_id}'
        embed = discord.Embed(color=YT_COLOR, title=video_title, url=video_url, timestamp=datetime.now())
        embed.set_author(name=channel_title, url=channel_url, icon_url=channel_icon_url)
        embed.set_thumbnail(url=channel_icon_url)
        embed.set_image(url=video_thumbnail_url)
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        
        video_duration_dict = self.yt_api.analyze_data(video_info, ['contentDetails', 'duration'])
        video_duration = self.__duration_transfer(video_duration_dict)
        video_status = self.yt_api.analyze_data(video_info, ['snippet', 'liveBroadcastContent'])
        if video_status == "none":
            if self.yt_api.analyze_data(video_info, ['liveStreamingDetails']) is None:
                # 一般影片
                embed.add_field(name="Status", value="Video", inline=True)
                embed.add_field(name="Video Length", value=video_duration, inline=True)
                published = self.__isoformat_transfer(video_info, ['snippet', 'publishedAt'])
                embed.add_field(name="Published Time", value=published, inline=False)
            else:
                # 已結束live
                embed.add_field(name="Status", value="Live", inline=True)
                embed.add_field(name="Live Status", value="Ended", inline=True)
                end_time = self.__isoformat_transfer(video_info, ['liveStreamingDetails', 'actualEndTime'])
                embed.add_field(name="End Time", value=end_time, inline=False)
                embed.add_field(name="Video Length", value=video_duration, inline=True)
        elif video_status == "live":
            # live中
            embed.add_field(name="Status", value="Streaming", inline=True)
            embed.add_field(name="Live Status", value="Live", inline=True)
            scheduled_start = self.__isoformat_transfer(video_info, ['liveStreamingDetails', 'scheduledStartTime'])
            embed.add_field(name="Start Time", value=scheduled_start, inline=False)
        elif video_status == "upcoming":
            # live即將開始
            embed.add_field(name="Status", value="Live", inline=True)
            embed.add_field(name="Live Status", value="Upcoming", inline=True)
            scheduled_start = self.__isoformat_transfer(video_info, ['liveStreamingDetails', 'scheduledStartTime'])
            embed.add_field(name="Scheduled Start Time", value=scheduled_start, inline=False)
            
        return embed
    
    
    @tasks.loop(minutes=5)
    async def update_new_video(self):
        data = self.db.get_yt_users()
        
        for useranme, info in data.items():
            if info['follower_cnt'] == 0:
                data[useranme]['last_updated'] = datetime.now(timezone.utc).isoformat()
                continue
            new_video_infos, last_updated = self.yt_api.get_new_videos(info['upload_id'], datetime.fromisoformat(info['last_updated']))
            new_video_embeds = [self.__create_embed(video_info, info['icon_url']) for video_info in new_video_infos]
            for follower in self.db.get_followers('yt', useranme):
                if user := self.bot.get_user(int(follower)):
                    for i in range(0, len(new_video_embeds), MAX_EMBED_LIMIT):
                        await user.send(embeds=new_video_embeds[i:i+MAX_EMBED_LIMIT])
            data[useranme]['last_updated'] = last_updated.isoformat()
        self.db.update_yt_users(data)
        
    @tasks.loop(hours=24)
    async def update_channel_info(self):
        data = self.db.get_yt_users()
        for username in data.keys():
            info = self.yt_api.get_channel_info(user_id=data[username]['id'])
            data[username]['title'] = info['title']
            data[username]['icon_url'] = info['icon_url']
            data[username]['description'] = info['description']
        self.db.update_x_users(data)

# Cog 載入 Bot 中
async def setup(bot: commands.Bot):
    await bot.add_cog(Youtube(bot))
