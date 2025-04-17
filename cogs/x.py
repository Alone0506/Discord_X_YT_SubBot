import asyncio
from collections import deque
import logging

from discord.ext import commands, tasks

from api.x_api import XAPI
from utils import DB


logger = logging.getLogger('bot')

class X(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.x_api = XAPI()
        self.user_q = deque()
        self.db = DB().create_db()
        
    # 當機器人完成啟動時
    async def cog_load(self):
        self.update_new_tweets.start()
        self.update_channel_info.start()
        
    async def cog_unload(self):
        self.update_new_tweets.cancel()
        self.update_channel_info.cancel()

    # 因為 api 有使用限制, 所以設定固定時間檢查一位 x's user 的新 post
    @tasks.loop(minutes=2)
    async def update_new_tweets(self):
        """
        找出在queue中且有人訂閱的名子然後使用x api, 只後私訊所有訂閱者,
        """
        data = self.db.get_x_users()
        if len(self.user_q) == 0:
            self.user_q = deque(data.keys())
            
        while self.user_q and self.user_q[0] not in data:
            self.user_q.popleft()
        if len(self.user_q) == 0:
            return
            
        username = self.user_q.popleft()
        new_tweets_url, last_post_id = await self.x_api.get_new_tweets(username, data[username]['last_post_id'])
        if new_tweets_url:
            for follower in self.db.get_followers('x', username):
                user = self.bot.get_user(int(follower))
                if user is not None:
                    await user.send(content='\n'.join(new_tweets_url))
        data[username]['last_post_id'] = last_post_id
        self.db.update_x_users({username: data[username]})
        
    
    @tasks.loop(hours=24)
    async def update_channel_info(self):
        data = self.db.get_x_users()
        for username in data.keys():
            info = await self.x_api.get_user_info(username)
            if info == {}:
                continue
            data[username]['title'] = info['title']
            data[username]['icon_url'] = info['icon_url']
            data[username]['description'] = info['description']
            await asyncio.sleep(60)
        self.db.update_x_users(data)
    
# Cog 載入 Bot 中
async def setup(bot: commands.Bot):
    await bot.add_cog(X(bot))