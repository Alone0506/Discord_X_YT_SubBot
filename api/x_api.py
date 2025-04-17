import logging
import os
import tweety
from tweety.types.twDataTypes import Tweet, User
import asyncio
import sys

X_USERNAME = os.getenv("X_USERNAME", "")
X_PASSWORD = os.getenv("X_PASSWORD", "")

logger = logging.getLogger('api')

class XAPI:
    def __init__(self):
        # login
        self.app = tweety.Twitter('session')
        self.initialized = False

        # 避免get_user_info時出現 OSError: [WinError 6]
        logger.info(f"system plarform: {sys.platform}")
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
    async def initialize(self):
        """
        非同步初始化函數，必須在使用其他方法前呼叫
        """
        try:
            await self.app.start(X_USERNAME, X_PASSWORD)
        except Exception as e:
            logger.error(f"Error in x_api.py: initialize: {e}")
            return
        self.initialized = True
        
    async def get_user_info(self, username: str) -> dict:
        """
        input:
            username: user's x id
        output:
            dict: user info
        """
        # 確保已初始化
        if not self.initialized:
            await self.initialize()
        
        try:
            user: User = await self.app.get_user_info(username)
            _, last_post_id = await self.get_new_tweets(username, "0")
        except Exception as e:
            logger.error(f"Error in x_api.py: get_user_info: {e}")
            return {}
        return {
            "title": user.name,
            "icon_url": user.profile_image_url_https,
            "description": user.description,
            "last_post_id": last_post_id,
        }
    
    async def get_new_tweets(self, username: str, last_post_id: str) -> tuple[list[str], str]:
        """
        input:
            username: user's x id
            last_post_id: user's last post id
        output:
            list[str]: 所有 post's id > last_post_id 的 post's url
            last_post_id: 所有new posts's id 與 last_post_id 的最大值
        """
        try:
            if not self.initialized:
                await self.initialize()
            
            valid_tweets:list[Tweet] = []
            tweets = await self.app.get_tweets(username)
            for tweet in tweets.tweets:
                if isinstance(tweet, Tweet) and int(tweet.id) > int(last_post_id) and not tweet.is_retweet:
                    valid_tweets.append(tweet)
                    
            valid_tweets.sort(key=lambda x: x.id)
            if valid_tweets:
                last_post_id = str(valid_tweets[-1].id)
                            
            return [x.url for x in valid_tweets], last_post_id
    
        except Exception as e:
            logger.error(f"Error in x_api.py: get_new_tweets: {e}")
            return [], last_post_id