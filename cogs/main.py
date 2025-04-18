import logging

import discord
from discord import app_commands
from discord.ext import commands

from api.x_api import XAPI
from api.yt_api import YoutubeAPI
from utils import YT_COLOR, X_COLOR, SUB_EMBED_COLOR, MAX_EMBED_LIMIT, MAX_OPTION_LIMIT, DB

logger = logging.getLogger('discord')


class YTUserEmbed(discord.Embed):
    def __init__(self, username: str, info: dict[str, str]):
        super().__init__(
            color=YT_COLOR, 
            title=info['title'], 
            url=f'https://www.youtube.com/@{username}', 
            description = info['description']
        )
        self.set_thumbnail(url=info['icon_url'])
        
        
class XUserEmbed(discord.Embed):
    def __init__(self, username: str, info: dict[str, str]):
        super().__init__(
            color=X_COLOR, 
            title=info['title'], 
            url=f'https://x.com/{username}', 
            description = info['description']
        )
        self.set_thumbnail(url=info['icon_url'])

class SubView(discord.ui.View):
    def __init__(self, dc_id: str, db: DB, timeout: int=180, placeholder: str="選擇要訂閱的內容創作者"):
        super().__init__(timeout=timeout)
        self.dc_id = dc_id
        self.db = db
        self.yt_value_prefix = "YT"
        self.x_value_prefix = "X"

        self.select = discord.ui.Select(
            placeholder=placeholder,
            min_values=0,
        )
        self.add_item(self.select)
        self.initial_select()  # initial options for select menu by dc_id
        
    def initial_select(self):
        yt_sub, x_sub = self.db.get_dc_user_subs(self.dc_id)
        
        for username, info in self.db.get_yt_users().items():
            self.select.add_option(
                label=f'{self.yt_value_prefix} - {info["title"]}',
                value=self.yt_value_prefix + username,
                default=username in yt_sub
            )
        for username, info in self.db.get_x_users().items():
            self.select.add_option(
                label=f'{self.x_value_prefix} - {info["title"]}',
                value=self.x_value_prefix + username,
                default=username in x_sub
            )
        if len(self.select.options) == 0:
            self.select.placeholder = "目前沒有可訂閱的頻道"
            self.select.disabled = True
            self.select.add_option(label="無可用頻道", value="None")
            return
        self.select.max_values = min(len(self.select.options), 25)


class SubEmbed(discord.Embed):
    def __init__(self, dc_id: str, db: DB):
        super().__init__(color=SUB_EMBED_COLOR)
        self.title = "訂閱中"
        yt_sub_username, x_sub_username = db.get_dc_user_subs(dc_id)

        yt_sub_title = [user['title'] for user in db.get_yt_users(usernames=yt_sub_username).values()]
        x_sub_title = [user['title'] for user in db.get_x_users(usernames=x_sub_username).values()]
        
        yt_value = []
        for title, username in zip(yt_sub_title, yt_sub_username):
            yt_value.append(f'[{title}](https://www.youtube.com/@{username})')
        if yt_value == []:
            yt_value = ["None"]
            
        x_value = []
        for title, username in zip(x_sub_title, x_sub_username):
            x_value.append(f'[{title}](https://x.com/{username})')
        if x_value == []:
            x_value = ["None"]
        
        self.description = (
            "### YT\n"
            + '\n'.join(yt_value) + "\n"
            + "### X\n"
            + '\n'.join(x_value)
        )
        
        
class Main(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DB().create_db()

    @app_commands.command(name = "list_content_creator", description = "View content creator")
    async def list_content_creator(self, interaction: discord.Interaction):
        embeds: list[discord.Embed] = []
        
        for username, info in self.db.get_yt_users().items():
            embeds.append(YTUserEmbed(username, info))
            
        for username, info in self.db.get_x_users().items():
            embeds.append(XUserEmbed(username, info))
    
        if len(embeds) == 0:
            await interaction.response.send_message(content="目前沒有可訂閱的頻道", ephemeral=True)
        else:
            msg = "🟥: YT, ⬛: X"
            await interaction.response.send_message(content=msg, embeds=embeds[:MAX_EMBED_LIMIT], ephemeral=True)
            for i in range(MAX_EMBED_LIMIT, len(embeds), MAX_EMBED_LIMIT):
                await interaction.followup.send(embeds=embeds[i:i+MAX_EMBED_LIMIT], ephemeral=True)
            
            
    @app_commands.command(name = "subscribe", description = "Sub content creator")
    async def subscribe(self, interaction: discord.Interaction):
        subview = SubView(str(interaction.user.id), self.db, timeout=180, placeholder="選擇要訂閱的內容創作者")
        
        async def select_callback(interaction: discord.Interaction):
            dc_id = str(interaction.user.id)
            old_yt_subs, old_x_subs = self.db.get_dc_user_subs(dc_id)
            old_yt_subs, old_x_subs = set(old_yt_subs), set(old_x_subs)
            new_yt_subs = set([v[len(subview.yt_value_prefix):] for v in subview.select.values if v.startswith(subview.yt_value_prefix)])
            new_x_subs = set([v[len(subview.x_value_prefix):] for v in subview.select.values if v.startswith(subview.x_value_prefix)])
            
            self.db.add_dc_user_subs(dc_id, list(new_yt_subs - old_yt_subs), list(new_x_subs - old_x_subs))
            self.db.del_dc_user_subs(dc_id, list(old_yt_subs - new_yt_subs), list(old_x_subs - new_x_subs))
            
            await interaction.response.send_message(
                content="訂閱設定完成",
                embed=SubEmbed(dc_id, self.db),
                ephemeral=True
            )
        subview.select.callback = select_callback
        await interaction.response.send_message(view=subview, ephemeral=True)
        
        
    @app_commands.command(name = "list_subscribe", description = "List the Sub content creator")
    async def list_subscribe(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=SubEmbed(str(interaction.user.id), self.db), ephemeral=True)
        
        
    @app_commands.command(name='add_content_creator', description='Add content creator')
    @app_commands.describe(platform = "平台 (YT or X)", username = "User name")
    @app_commands.choices(
        platform = [
            app_commands.Choice(name = "YT", value = "YT"),
            app_commands.Choice(name = "X", value = "X"),
        ]
    )
    async def add_content_creator(self, interaction: discord.Interaction, platform: str, username: str):
        """
        platform: str, YT or X
        username: str, YT's username or X's username
        """
        await interaction.response.defer(ephemeral=True)
        
        total_user_cnt = len(self.db.get_yt_users()) + len(self.db.get_x_users())
        if total_user_cnt >= MAX_OPTION_LIMIT:
            await interaction.followup.send(content=f"支援的用戶總數已超出上限 ({MAX_OPTION_LIMIT}), 請刪除一些 X or YT 用戶", ephemeral=True)
            return
        
        if username.startswith('@'):
            username = username[1:]
            
        if platform == 'YT':
            if self.db.get_yt_users(usernames=[username]):
                await interaction.followup.send(content="頻道已存在", ephemeral=True)
                return

            if yt_data := YoutubeAPI().get_channel_info(username=username):
                self.db.add_yt_user(username, yt_data)
                await interaction.followup.send(content="頻道已新增", embed=YTUserEmbed(username, yt_data), ephemeral=True)
            else:
                await interaction.followup.send(content="頻道不存在或輸入錯誤", ephemeral=True)
                
                    
        elif platform == 'X':
            if self.db.get_x_users(usernames=[username]):
                await interaction.followup.send(content="頻道已存在", ephemeral=True)
                return
            
            if x_data := await XAPI().get_new_user_info(username):
                self.db.add_x_user(username, x_data)
                await interaction.followup.send(content="頻道已新增", embed=XUserEmbed(username, x_data), ephemeral=True)
            else:
                await interaction.followup.send(content="頻道不存在或輸入錯誤", ephemeral=True)

    
    @app_commands.command(name='delete_content_creator', description='Delete content creator')
    async def delete_content_creator(self, interaction: discord.Interaction):
        unsubview = SubView(str(interaction.user.id), self.db, timeout=180, placeholder="選擇要刪除的內容創作者")
        for i in range(len(unsubview.select.options)):
            unsubview.select.options[i].default = False
            
        async def select_callback(interaction: discord.Interaction):
            yt_prefix, x_prefix = unsubview.yt_value_prefix, unsubview.x_value_prefix
            yt_del = set([value[len(yt_prefix):] for value in unsubview.select.values if value.startswith(yt_prefix)])
            x_del = set([value[len(x_prefix):] for value in unsubview.select.values if value.startswith(x_prefix)])
            
            # del dc user data
            self.db.del_yt_users(list(yt_del))
            self.db.del_x_users(list(x_del))
            await interaction.response.send_message(content="已刪除", ephemeral=True)
        
        unsubview.select.callback = select_callback
        await interaction.response.send_message(view=unsubview, ephemeral=True)


    # 當機器人完成啟動時
    @commands.Cog.listener()
    async def on_ready(self):
        slash = await self.bot.tree.sync()
        logger.info(f'{self.bot.user} 已登入, 載入 {len(slash)} 個斜線指令')
        game = discord.Game('YT & X')
        await self.bot.change_presence(status=discord.Status.online, activity=game)

# Cog 載入 Bot 中
async def setup(bot: commands.Bot):
    await bot.add_cog(Main(bot))
