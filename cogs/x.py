from collections import deque
import logging

from discord.ext import commands, tasks

from api.x_api import XAPI
from utils import DB


logger = logging.getLogger('discord')

class X(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.x_api = XAPI()
        self.user_q = deque()
        self.db = DB().create_db()
        
    # 當機器人完成啟動時
    async def cog_load(self):
        await self.x_api.initialize()
        self.update_new_tweets.start()
        
    async def cog_unload(self):
        self.update_new_tweets.cancel()

    # 因為 api 有使用限制, 所以設定固定時間檢查一位 x's user 的新 tweet
    @tasks.loop(minutes=2)
    async def update_new_tweets(self):
        """
        找出在queue中且有人訂閱的名子然後使用x api, 只後私訊所有訂閱者,
        """
        logger.info('start update new tweets')
        
        data = self.db.get_x_users()
        if len(self.user_q) == 0:
            self.user_q = deque(data.keys())
            
        # avoid username in queue but not in database
        while self.user_q and self.user_q[0] not in data:
            self.user_q.popleft()
        if len(self.user_q) == 0:
            return
            
        username = self.user_q.popleft()
        new_tweet_urls, author_info, last_updated = await self.x_api.get_new_tweets(username, data[username]['last_updated'])
        if new_tweet_urls:
            for follower in self.db.get_followers('x', username):
                user = self.bot.get_user(int(follower))
                if user is not None:
                    await user.send(content='\n'.join(new_tweet_urls))
            data[username]['title'] = author_info['title']
            data[username]['icon_url'] = author_info['icon_url']
            data[username]['description'] = author_info['description']
        data[username]['last_updated'] = last_updated
        self.db.update_x_users({username: data[username]})
    
# Cog 載入 Bot 中
async def setup(bot: commands.Bot):
    await bot.add_cog(X(bot))