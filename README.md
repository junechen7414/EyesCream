Python version 3.7 or newer

在專案目錄下建立 venv 虛擬環境
```bash
py -m venv venvName
```

activate.bat 啟用虛擬環境  
Windows
```bash
venv\Scripts\activate
```
macOS or Linux
```bash
source venv/bin/activate
```

安裝套件
```bash
pip install -r requirements.txt
```

在專案目錄下建立config.py，將其中```your_notion_token```以及```your_notion_database_id```替換為實際值
```
from datetime import datetime, timedelta

# 常量
PTT_BASE_URL = "https://www.ptt.cc"
PTT_COOKIES = {'over18': '1'}

# Notion 配置
NOTION_SECRET = "your_notion_token"
DATABASE_ID = "your_notion_database_id"

# 圖片相關配置
NOTION_CHUNK_SIZE = 100  #Notion 分頁中圖片數量最多為100，也可設定較小數字
IMAGE_BLACKLIST = [  #常見的推廣社群軟體
    "instagram",  
    "facebook",  
    "tiktok", 
    "https://x.com/",  
    "twitter",
    "youtube",
    "https://youtu"
]

def get_yesterday_date():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday

def get_today_date():
    today = datetime.now()
    return today

```
