# 說明 / Introduction
以前的說明(已過時)[每日排程爬蟲PTT圖片上傳Notion圖庫](https://ithelp.ithome.com.tw/articles/10369755)  

之所以要換做法是因為每天如果到排程的時段電腦就關機了就沒有辦法執行了，畢竟是本地端的爬蟲，PTT又有限制不能夠用雲端連線，於是權衡之後改成爬蟲一個日期區間的文章中的圖片。  
大部分的內容還是跟之前說明的文章一樣，只是爬蟲的演算法有經過修正，從本來的日期迴圈換成文章迴圈，應會在效能上省去原先一些不必要的消耗。  
***
Python version 3.7 or newer

在專案目錄下建立 venv 虛擬環境
```bash
py -m venv venvName
```

activate.bat 啟用虛擬環境  
Windows
```bash
venvName\Scripts\activate
```
macOS or Linux
```bash
source venvName/bin/activate
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

# 設定最多爬取幾頁，避免無限循環
MAX_PAGE = 100

# 圖片相關配置
NOTION_CHUNK_SIZE = 100  #Notion 分頁中圖片數量最多為100，也可設定較小數字
IMAGE_BLACKLIST = [  #常見的推廣社群軟體
    "instagram",  
    "facebook",  
    "tiktok", 
    "https://x.com/",  
    "twitter",
    "youtube",
    "https://youtu",
    "threads"
]

# 設定爬取的日期區間 (YYYY, MM, DD)
START_DATE = datetime(2025, 5, 22)
END_DATE = datetime(2025, 5, 24)

```
最後再使用管理員權限執行批次檔
