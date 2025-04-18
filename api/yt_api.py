from datetime import datetime
import os
import logging

from googleapiclient.discovery import build

YT_API_KEY = os.getenv("YT_API_KEY", "")

logger = logging.getLogger('discord')

class YoutubeAPI:
    def __init__(self):
        self.youtube = build('youtube', 'v3', developerKey=YT_API_KEY)
        
    def analyze_data(self, data: dict, paths: list[str]):
        for path in paths:
            if path in data:
                data = data[path]
            else:
                return None
        return data
        
    def get_new_videos(self, uploads_id: str, last_updated: datetime) -> tuple[list[dict], datetime]:
        """
        消耗api (1 + 新影片數)配額
        input:
            uploads_id: user's uploads id
            server_update_time: server json內所記載的時間
        output:
            list[dict]: 所以上傳時間>new_update_time的影片資訊
            datetime: 所有new video的上傳時間與server_update_time的最大值
        """
        new_videos = []
        new_last_updated = last_updated
        
        for video in self.__get_video_list(uploads_id):
            upload_time_str = self.analyze_data(video, ['snippet', 'publishedAt'])
            if not upload_time_str:
                continue
                
            upload_time = datetime.fromisoformat(upload_time_str)
            if upload_time > last_updated:
                if video_id := self.analyze_data(video, ['contentDetails', 'videoId']):
                    new_last_updated = max(new_last_updated, upload_time)
                    new_videos.append(self.__get_video_info(video_id))
            
        return new_videos, new_last_updated

    
    def get_channel_info(self, username: str=None, user_id: str=None) -> dict:
        """
        獲取頻道資訊，支援頻道 ID 或 @用戶名

        參數:
            username: YT用戶名,
            user_id: 頻道 ID (格式如: UC...)

        消耗api:
            - 使用 @用戶名: 2 配額
            - 使用 頻道 ID: 1 配額
        
        返回:
            dict: 頻道資訊字典，如果找不到頻道則返回空字典
            {
                'id':
                'title':
                'icon_url':
                'uploads_id':
                'description':
            }
        """
        if user_id is None:
            user_id = self._username2userid(username)
        if user_id is None:
            return {}
        
        request = self.youtube.channels().list(
            part='id, snippet, contentDetails', 
            id=user_id
        )
        response = request.execute()
        if 'items' not in response or len(response['items']) == 0:
            return {}
        
        response = response['items'][0]
        return {
            'id': response['id'],
            'title': response['snippet']['title'],
            'icon_url': response['snippet']['thumbnails']['default']['url'],
            'uploads_id': response['contentDetails']['relatedPlaylists']['uploads'],
            'description': response['snippet']['description'],
        }
    
    def _username2userid(self, username: str) -> str | None:
        """
        將 @用戶名 轉換為頻道 ID
        """
        request = self.youtube.search().list(
            q=username,
            part='snippet',
            type='channel',
            maxResults=1
        )
        response = request.execute()
        if 'items' not in response or len(response['items']) == 0:
            return None
        return response['items'][0]['id']['channelId']
    
    def __get_video_list(self, uploads_id: str) -> dict:
        """
        消耗api 1配額
        """
        request = self.youtube.playlistItems().list(
            part='contentDetails, snippet',
            playlistId=uploads_id,
            maxResults=50,
        )
        response = request.execute()
        return response['items']
    
    def __get_video_info(self, video_id: str) -> dict:
        """
        消耗api 1配額
        """
        request = self.youtube.videos().list(part='id, snippet, contentDetails, liveStreamingDetails', id=video_id)
        response = request.execute()
        return response['items'][0]

    