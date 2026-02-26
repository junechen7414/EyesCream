import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# PTT 相關配置
PTT_BASE_URL = "https://www.ptt.cc"
PTT_COOKIES = {'over18': '1'}
MAX_PAGE = 500
START_DATE = date(2026, 1, 3)
END_DATE = date(2026, 1, 31)

# 圖片相關配置
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

# Notion 相關配置
NOTION_SECRET = os.getenv("NOTION_SECRET")
DATABASE_ID = os.getenv("DATABASE_ID")
NOTION_CHUNK_SIZE = 100 # Notion API 單次建立 block 的上限