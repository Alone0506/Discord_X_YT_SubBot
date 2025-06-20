import asyncio
from datetime import datetime
import logging
import os
from pathlib import Path
import sys

import tweety
from tweety.types.twDataTypes import Tweet, User


logger = logging.getLogger('discord')


"""避免get_user_info時出現 OSError: [WinError 6]"""
logger.info(f"system plarform: {sys.platform}")
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

X_USERNAME = os.getenv("X_USERNAME", "")
X_PASSWORD = os.getenv("X_PASSWORD", "")
app = tweety.Twitter(str(Path(__file__).parent.parent / 'db' / 'x_session'))
initialized = False


class XAPI:
    async def initialize(self):
        global initialized
        if not initialized:
            await app.start(X_USERNAME, X_PASSWORD)
            initialized = True
    
    async def get_new_user_info(self, username: str) -> dict[str, str]:
        """
        input:
            username: the username of an X user
        output:
            dict: user info, include:
                - 'title': user's name
                - 'icon_url': user's icon url
                - 'description': user's description
        """
        await self.initialize()
        
        try:
            user: User = await app.get_user_info(username)
            return {
                "title": user.name,
                "icon_url": user.profile_image_url_https,
                "description": user.description,
            }
            
        except Exception as e:
            logger.error(f"Error in x_api.py: get_new_user_info: {e}")
            return {}
    
    async def get_new_tweets(self, username: str, last_updated_str: str) -> tuple[list[str], list[dict[str, str]], str]:
        """
        取得使用者自上次更新後發布的所有新推文。
        
        過濾條件:
        1. 排除非 Tweet 類型的內容
        2. 排除轉推 (Retweet)
        3. 只保留在 last_updated 時間之後發布的推文
        
        input:
            username: X 平台上的使用者名稱或 ID
            last_updated_str: , ISO 格式的時間字符串，表示上次檢查的時間點
            
        output:
            urls: 所有新推文的 URL 列表，按發布時間由早到晚排序
            author_info: 作者信息，包含以下鍵值:
                - 'name': 作者名稱
                - 'icon_url': 作者頭像 URL
                - 'description': 作者個人簡介
            latest_time: 最新推文的發布時間 (ISO 格式)，如無新推文則為輸入的 last_updated_str
            
        Raises:
            如有異常會被捕獲並記錄到日誌，函數會返回空列表、空字典和原始的 last_updated_str。
        
        Example:
            ```python
            urls, author_info, latest_time = await api.get_new_tweets('elonmusk', '2023-04-18T12:00:00+00:00')
            for url in urls:
                print(f"發現新推文: {url}")
            ```
        """
        await self.initialize()
        
        def valid_tweet(tweet, last_updated: datetime) -> bool:
            if not isinstance(tweet, Tweet):
                return False
            if tweet.is_retweet:
                return False
            if tweet.created_on <= last_updated:
                return False
            return True
        
        try:
            last_updated: datetime = datetime.fromisoformat(last_updated_str)
            tweets = await app.get_tweets(username)
            valid_tweets = [tweet for tweet in tweets.tweets if valid_tweet(tweet, last_updated)]
            valid_tweets.sort(key=lambda x: x.created_on)
            
            urls = [tweet.url for tweet in valid_tweets]
            
            author_info = {}
            if tweets:
                author_info = {
                    'title': tweets[0].author.name,
                    'icon_url': tweets[0].author.profile_image_url_https,
                    'description': tweets[0].author.description,
                }
            else:
                await asyncio.sleep(10)
                author_info = await self.get_new_user_info(username)
            
            if valid_tweets:
                last_updated_str = valid_tweets[-1].created_on.isoformat()
                
            return urls, author_info, last_updated_str
            
        except Exception as e:
            logger.error(f"Error in x_api.py: get_new_tweets: {e}")
            logger.error(f"error message: {str(e)}")
            
            # 清除舊的 session 檔案
            if session_path := Path(__file__).parent.parent / 'db' / 'x_session':
                if session_path.exists():
                    session_path.unlink()
                    logger.info(f"Deleted session file: {session_path}")
            global app
            app = tweety.Twitter(str(Path(__file__).parent.parent / 'db' / 'x_session'))
            await app.start(X_USERNAME, X_PASSWORD)
            
            return [], {}, last_updated_str
