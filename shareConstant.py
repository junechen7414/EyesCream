from datetime import datetime, timedelta, date # 導入 date 類別

# 共用的常量
PTT_BASE_URL = "https://www.ptt.cc"
PTT_COOKIES = {'over18': '1'}


# 圖片相關配置
NOTION_CHUNK_SIZE = 100
IMAGE_BLACKLIST = [
    "instagram",  
    "facebook",  
    "tiktok", 
    "https://x.com/",  
    "twitter",
    "youtube",
    "https://youtu",
    "threads"
]

# 設定最多爬取幾頁，避免無限循環
MAX_PAGE = 100

# 設定爬取的日期區間 (YYYY, MM, DD)
START_DATE = date(2025, 9, 12)
END_DATE = date(2025, 9, 19)
