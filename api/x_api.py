import asyncio
import logging
import os
from pathlib import Path
import sys

import tweety
from tweety.types.twDataTypes import Tweet, User

X_USERNAME = os.getenv("X_USERNAME", "")
X_PASSWORD = os.getenv("X_PASSWORD", "")

# 基礎路徑和會話存儲路徑
BASE_PATH = Path(__file__).parent.parent
SESSION_PATH = str(BASE_PATH / 'db' / 'x_session')

logger = logging.getLogger('api')

class XAPI:
    _instance = None  # 儲存單一實例
    _initialization_lock = asyncio.Lock()
    _initialized = False  # 標記是否已初始化
    
    def __new__(cls, *args, **kwargs):
        # 確保只建立一個實例
        if cls._instance is None:
            cls._instance = super(XAPI, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.app = tweety.Twitter(SESSION_PATH)
            
    async def initialize(self):
        """確保只初始化一次的非同步方法"""
        if not XAPI._initialized:
            # 使用鎖確保多個協程同時調用時只執行一次初始化
            async with XAPI._initialization_lock:
                # 再次檢查，防止其他協程在等待鎖時已初始化
                if not XAPI._initialized:
                    try:
                        # 避免get_user_info時出現 OSError: [WinError 6]
                        logger.info(f"system plarform: {sys.platform}")
                        if sys.platform == 'win32':
                            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                        
                        await self.app.start(X_USERNAME, X_PASSWORD)
                        XAPI._initialized = True
                        logger.info("XAPI initialized successfully")
                    except Exception as e:
                        logger.error(f"Error initializing XAPI: {e}")
                        
        
    async def get_user_info(self, username: str) -> dict:
        """
        input:
            username: user's x id
        output:
            dict: user info
        """
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
        await self.initialize()
        
        try:
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