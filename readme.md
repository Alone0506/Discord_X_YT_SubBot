# Discord YT & X 訂閱機器人

這是一個 Discord 機器人，專門用於訂閱 YouTube 頻道與 X（原Twitter）帳號的最新動態。機器人會定期檢查訂閱的內容創作者是否有新內容，並將新影片或貼文直接發送給訂閱者。

## 功能特色

- **YouTube 訂閱功能**
  - 追蹤頻道新影片上傳
  - 區分一般影片與直播內容
  - 提供影片詳細資訊（長度、狀態、上傳時間等）

- **X（Twitter）訂閱功能**
  - 自動追蹤 X 平台用戶的新貼文
  - 提供貼文連結

- **完整的訂閱管理系統**
  - 使用者可自行訂閱/取消訂閱
  - 支援多頻道/帳號管理
  - 智慧化更新檢測機制

## 部署前置條件

- Python 3.11.9
- Discord 機器人 Token
- YouTube API 金鑰
- X（Twitter）帳號及密碼

## 安裝與部署步驟

1. **複製專案**
   ```
   git clone https://github.com/Alone0506/Discord_X_YT_SubBot.git
   ```

2. **建立虛擬環境**
   #### Windows
   ```
   python -m venv .venv
   ```
   #### Linux / maxOS
   ```
   python3 -m venv .venv
   ```

3. **安裝依賴套件**
   ```
   pip install -r requirements.txt
   ```

4. **設定環境變數**

   建立 `.env` 檔案或設定系統變數並新增以下變數：
   ```
   BOT_TOKEN = 你的 Discord 機器人 Token
   YT_API_KEY = 你的 YouTube API 金鑰
   X_USERNAME = 你的 X 帳號
   X_PASSWORD = 你的 X 密碼
   ```

5. **初始化資料庫**

   資料庫會在第一次運行時自動初始化

6. **啟動機器人**
   ```
   python bot.py
   ```
## 部屬到雲端

依照以下文章可用 Docker Hub 部屬在 Synology Nas 上運作:

1. [如何使用 Docker 打包 Discord Bot 並發佈到 Docker Hub](https://ted.familyds.com/2025/03/10/%e5%a6%82%e4%bd%95%e4%bd%bf%e7%94%a8-docker-%e6%89%93%e5%8c%85-discord-bot-%e4%b8%a6%e7%99%bc%e4%bd%88%e5%88%b0-docker-hub/)
2. [使用 Synology Container Manager 部屬 Discord Bot](https://ted.familyds.com/2025/03/10/%e4%bd%bf%e7%94%a8-synology-container-manager-%e9%83%a8%e5%b1%ac-discord-bot/)

## 部屬到 Linux 注意事項

如果要部屬到 Linux 上的話, 因為 requirement 裡面的 python-magic-bin==0.4.14 套件只適用於 Windows, 需要將 requirement.txt 內的 `python-magic-bin==0.4.14` 刪除, 另外安裝 libmagic 來代替

## 機器人指令說明

機器人使用 Discord 斜線指令，提供以下指令：

| 指令 | 說明 |
|------|------|
| `/list_content_creator` | 查看所有可訂閱的內容創作者 |
| `/subscribe` | 訂閱 / 取消訂閱內容創作者 |
| `/list_subscribe` | 查看自己目前訂閱的內容創作者 |
| `/add_content_creator` | 新增內容創作者 (需指定平台與用戶名) |
| `/delete_content_creator` | 刪除內容創作者 |

輸入用戶名時支援有 @ 或無 @ 開頭的用戶名

### 指令使用範例

- **新增內容創作者**
  支援有 @ 或無 @開頭的用戶名
  ```
  /add_content_creator platform: YT username: @Ayase_YOASOBI
  ```
  或
  ```
  /add_content_creator platform: X username: @YOASOBI_staff
  ```

- **查看訂閱列表**
  ```
  /list_subscribe
  ```

## 技術說明

- 資料庫使用 SQLite 儲存訂閱關係與內容創作者資訊
- YouTube 部分使用 Google API
- X（Twitter）部分使用第三方 API 庫 - [tweety](https://github.com/mahrtayyab/tweety/tree/main)
- 使用 Discord.py 建立 Discord 機器人
- 所有更新檢查均使用非同步任務，功能各自獨立

## 其餘事項

- YouTube API 有使用配額限制，請留意 API 使用量
- 由於使用第三方庫, 取得 X 的貼文時要注意時間間格
- YouTube 用影片的上傳時間來判斷是否有新影片
- 因為 X 使用 snowflake 來生成遞增的貼文 ID, 所以用 ID 來判斷是否有新影片
