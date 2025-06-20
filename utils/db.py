from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
from typing import Literal

from discord.utils import utcnow

logger = logging.getLogger('discord')

# 資料庫路徑
BASE_PATH = Path(__file__).parent.parent
DB_PATH = str(BASE_PATH / 'db' / 'sub.db')

class DB:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def _get_connection(self):
        """取得資料庫連接並啟用外鍵約束"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    @classmethod
    def create_db(cls) -> 'DB':
        """建立所需的資料表結構"""
        instance = cls()  # 先建立實例
        conn = instance._get_connection()  # 使用實例方法
        cursor = conn.cursor()
        
        # 建立資料表
        cursor.executescript('''
        -- YouTube 頻道資料表
        CREATE TABLE IF NOT EXISTS yt_users (
            username TEXT PRIMARY KEY,
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            icon_url TEXT,
            uploads_id TEXT,
            description TEXT,
            follower_cnt INTEGER DEFAULT 0,
            last_updated TEXT
        );

        -- X 使用者資料表
        CREATE TABLE IF NOT EXISTS x_users (
            username TEXT PRIMARY KEY,
            title TEXT,
            icon_url TEXT,
            description TEXT,
            follower_cnt INTEGER DEFAULT 0,
            last_updated TEXT
        );

        -- Discord-YouTube 訂閱關係
        CREATE TABLE IF NOT EXISTS dc_yt_sub (
            dc_id TEXT,
            yt_username TEXT,
            PRIMARY KEY (dc_id, yt_username),
            FOREIGN KEY (yt_username) REFERENCES yt_users(username) ON DELETE CASCADE
        );

        -- Discord-X 訂閱關係
        CREATE TABLE IF NOT EXISTS dc_x_sub (
            dc_id TEXT,
            x_username TEXT,
            PRIMARY KEY (dc_id, x_username),
            FOREIGN KEY (x_username) REFERENCES x_users(username) ON DELETE CASCADE
        );
        ''')

        # 建立訂閱 Trigger
        cursor.executescript('''
        -- 建立 YouTube 訂閱計數自動更新觸發器
        -- 新增訂閱時增加計數
        CREATE TRIGGER IF NOT EXISTS after_yt_sub_insert
        AFTER INSERT ON dc_yt_sub
        BEGIN
            UPDATE yt_users
            SET follower_cnt = follower_cnt + 1
            WHERE username = NEW.yt_username;
        END;

        -- 刪除訂閱時減少計數
        CREATE TRIGGER IF NOT EXISTS after_yt_sub_delete
        AFTER DELETE ON dc_yt_sub
        BEGIN
            UPDATE yt_users
            SET follower_cnt = follower_cnt - 1
            WHERE username = OLD.yt_username;
        END;

        -- 建立 X 訂閱計數自動更新觸發器
        -- 新增訂閱時增加計數
        CREATE TRIGGER IF NOT EXISTS after_x_sub_insert
        AFTER INSERT ON dc_x_sub
        BEGIN
            UPDATE x_users
            SET follower_cnt = follower_cnt + 1
            WHERE username = NEW.x_username;
        END;

        -- 刪除訂閱時減少計數
        CREATE TRIGGER IF NOT EXISTS after_x_sub_delete
        AFTER DELETE ON dc_x_sub
        BEGIN
            UPDATE x_users
            SET follower_cnt = follower_cnt - 1
            WHERE username = OLD.x_username;
        END;                  
        ''')

        conn.commit()
        conn.close()
        return instance
    
    # YouTube相關操作
    def get_yt_users(self, usernames: list[str] = []) -> dict[str, dict[str, str | int]]:
        """
        取得 YT 使用者資料
        如果有給 usernames, 則回傳這些使用者的資料
        如果沒有給 usernames, 則回傳所有使用者的資料

        return: dict, 鍵為username, 值為username資料字典
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if usernames:
            placeholders = ', '.join(['?'] * len(usernames))
            cursor.execute(f"SELECT * FROM yt_users WHERE username IN ({placeholders})", usernames)
        else:
            cursor.execute("SELECT * FROM yt_users")
        results = cursor.fetchall()
        conn.close()
        return {row['username']: dict(row) for row in results}

    def add_yt_user(self, username, channel_data):
        """新增YouTube使用者"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO yt_users 
                (username, id, title, icon_url, uploads_id, description, last_updated) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                username, 
                channel_data['id'],
                channel_data['title'],
                channel_data['icon_url'],
                channel_data['uploads_id'],
                channel_data['description'],
                utcnow().isoformat()
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"新增YouTube使用者失敗: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_yt_users(self, users_data: dict[str, dict[str, str | int]]) -> dict[str, bool]:
        """
        批量更新多個 YT 使用者資料
        :param users_data: 字典，鍵為使用者名稱，值為要更新的資料
        :return: 字典，鍵為使用者名稱，值為更新是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        results = {}
        
        try:
            for username, data in users_data.items():
                # 建立更新參數
                params = []
                query_parts = []
                
                for key, value in data.items():
                    if key in ['title', 'icon_url', 'description', 'last_updated']:
                        query_parts.append(f"{key} = ?")
                        params.append(value)
                
                if not query_parts:
                    results[username] = False
                    continue
                
                params.append(username)
                query = f"UPDATE yt_users SET {', '.join(query_parts)} WHERE username = ?"
                
                cursor.execute(query, params)
                results[username] = True
            
            conn.commit()
            return results
        except Exception as e:
            logger.error(f"更新多個 YT 使用者失敗: {e}")
            conn.rollback()
            return {username: False for username in users_data.keys()}
        finally:
            conn.close()

    def del_yt_users(self, usernames: list[str]) -> bool:
        """刪除多個 YT 使用者"""
        if not usernames:
            return True
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ', '.join(['?'] * len(usernames))
            cursor.execute(
                f"DELETE FROM yt_users WHERE username IN ({placeholders})",
                usernames
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"刪除多個 YouTube 使用者失敗: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # X相關操作
    def get_x_users(self, usernames: list[str] = []) -> dict[str, dict[str, str | int]]:
        """
        取得 X 使用者資料
        如果有給 usernames, 則回傳這些使用者的資料
        如果沒有給 usernames, 則回傳所有使用者的資料

        return: dict, 鍵為username, 值為username資料字典
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if usernames:
            placeholders = ', '.join(['?'] * len(usernames))
            cursor.execute(f"SELECT * FROM x_users WHERE username IN ({placeholders})", usernames)
        else:
            cursor.execute("SELECT * FROM x_users")
        results = cursor.fetchall()
        conn.close()
        return {row['username']: dict(row) for row in results}

    def add_x_user(self, username: str, data: dict[str, str]) -> bool:
        """
        新增X使用者資料到資料庫
        :param username: 使用者名稱
        :param data: 包含頻道標題、圖示URL和描述
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO x_users 
                (username, title, icon_url, description, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (
                username, 
                data['title'],
                data['icon_url'],
                data['description'],
                utcnow().isoformat()
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"新增 X 使用者失敗: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_x_users(self, users_data: dict[str, dict[str, str | int]]) -> dict[str, bool]:
        """
        批量更新多個X使用者資料
        :param users_data: 字典，鍵為使用者名稱，值為要更新的資料
        :return: 字典，鍵為使用者名稱，值為更新是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        results = {}
        
        try:
            for username, data in users_data.items():
                # 建立更新參數
                params = []
                query_parts = []
                
                for key, value in data.items():
                    if key in ['title', 'icon_url', 'description', 'last_updated']:
                        query_parts.append(f"{key} = ?")
                        params.append(value)
                
                if not query_parts:
                    results[username] = False
                    continue
                
                params.append(username)
                query = f"UPDATE x_users SET {', '.join(query_parts)} WHERE username = ?"
                
                cursor.execute(query, params)
                results[username] = True
            
            conn.commit()
            return results
        except Exception as e:
            logger.error(f"更新多個 X 使用者失敗: {e}")
            conn.rollback()
            return {username: False for username in users_data.keys()}
        finally:
            conn.close()


    def del_x_users(self, usernames: list[str]) -> bool:
        """刪除多個 X 使用者"""
        if not usernames:
            return True
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ', '.join(['?'] * len(usernames))
            cursor.execute(
                f"DELETE FROM x_users WHERE username IN ({placeholders})",
                usernames
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"刪除多個 X 使用者失敗: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
            

    # 訂閱相關操作
    def get_dc_user_subs(self, dc_id: str) -> tuple[list[str], list[str]]:
        """取得 dc user 的 yt & x 訂閱資料"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT yt_username FROM dc_yt_sub WHERE dc_id = ?", (dc_id,))
        yt_subs = [row['yt_username'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT x_username FROM dc_x_sub WHERE dc_id = ?", (dc_id,))
        x_subs = [row['x_username'] for row in cursor.fetchall()]
        
        conn.close()
        return yt_subs, x_subs

    def add_dc_user_subs(self, dc_id: str, yt: list[str], x: list[str]) -> bool:
        """新增訂閱"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if yt:
                cursor.executemany("""
                    INSERT OR IGNORE INTO dc_yt_sub (dc_id, yt_username)
                    VALUES (?, ?)
                """, [(dc_id, username) for username in yt])
            
            if x:
                cursor.executemany("""
                    INSERT OR IGNORE INTO dc_x_sub (dc_id, x_username)
                    VALUES (?, ?)
                """, [(dc_id, username) for username in x])
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DC 新增訂閱失敗: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def del_dc_user_subs(self, dc_id: str, yt: list[str], x: list[str]) -> bool:
        """移除訂閱"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if yt:
                placeholders = ', '.join(['?'] * len(yt))
                cursor.execute(
                    f"DELETE FROM dc_yt_sub WHERE dc_id = ? AND yt_username IN ({placeholders})",
                    [dc_id] + yt
                )
            if x:
                placeholders = ', '.join(['?'] * len(x))
                cursor.execute(
                    f"DELETE FROM dc_x_sub WHERE dc_id = ? AND x_username IN ({placeholders})",
                    [dc_id] + x
                )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"DC 移除訂閱失敗: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_followers(self, platform: Literal['yt', 'x'], username: str) -> list[str]:
        """取得 yt or x 的訂閱者列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if platform.lower() == 'yt':
                cursor.execute("""
                    SELECT dc_id FROM dc_yt_sub
                    WHERE yt_username = ?
                """, (username,))
            elif platform.lower() == 'x':
                cursor.execute("""
                    SELECT dc_id FROM dc_x_sub
                    WHERE x_username = ?
                """, (username,))
            
            followers = [row[0] for row in cursor.fetchall()]
            return followers
        except Exception as e:
            logger.error(f"取得 YT or X 訂閱者列表失敗: {e}")
            return []
        finally:
            conn.close()