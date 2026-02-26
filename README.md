# 前言 Introduction
選擇一個日期區間並僅限標題內容包含"正妹"字串且同時標題內容不包含"Cosplay"(personal preference)的文章把圖片蒐集起來上傳到個人的notion資料庫中，不下載到本地。
# 功能說明 Function
單執行序掃描ptt頁面從最新的頁面翻頁去蒐集要爬蟲起訖日中所有文章，多執行續的每個thread爬完圖片url(可過濾一些黑名單網址)後立即送到NotionUploader類別的buffer中以日期為key維護buffer bucket，如果單日累積到100個圖片url後使用notion create page api帶參數(蒐集的url們)上傳notion，而單日如果有150張圖片會分成日期為標題的100張圖和日期(2)為標題的50張圖，以此類推。
# 程式結構 Structure
## config.py
統一管理參數
```
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# PTT 設定
PTT_BASE_URL = "https://www.ptt.cc"
PTT_COOKIES = {'over18': '1'}
MAX_PAGE = 500
START_DATE = date(2025, 9, 20)
END_DATE = date(2026, 1, 1)

# 圖片黑名單
IMAGE_BLACKLIST = [
    "instagram", "facebook", "tiktok", "twitter", 
    "youtube", "youtu", "threads", "x.com"
]

# Notion 設定
NOTION_SECRET = os.getenv("NOTION_SECRET")
DATABASE_ID = os.getenv("DATABASE_ID")
NOTION_CHUNK_SIZE = 100  # Notion API 單次 children 上限
```
## ptt_scraper.py
專注於「從 HTML 變成 URL 列表」。
```
import requests
import time
import logging
from bs4 import BeautifulSoup as BS
from datetime import datetime, date
from typing import List, Tuple
from config import PTT_BASE_URL, IMAGE_BLACKLIST

logger = logging.getLogger(__name__)

def is_imgur_image_valid(url: str) -> bool:
    """檢查 Imgur 連結是否有效，避免抓到已移除的圖片"""
    invalid_urls = {"https://imgur.com/", "https://i.imgur.com/", "https://i.imgur.com/removed.png"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # allow_redirects=True 才能追蹤到 removed.png
        res = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        return res.status_code == 200 and res.url not in invalid_urls
    except:
        return False

def fetch_post_images(post_url: str, session: requests.Session) -> List[str]:
    """解析文章內文並回傳有效圖片連結"""
    try:
        res = session.get(post_url, timeout=15)
        res.raise_for_status()
    except Exception as e:
        logger.warning(f"無法存取文章 {post_url}: {e}")
        return []

    soup = BS(res.text, "html.parser")
    main_content = soup.find('div', id='main-content')
    if not main_content: return []

    links = []
    for content in main_content.contents:
        if isinstance(content, str) and "--" in content: break # 遇到簽名檔停止
        if content.name == 'a' and 'href' in content.attrs:
            url = content['href']
            if any(b in url for b in IMAGE_BLACKLIST): continue
            
            if "imgur.com" in url:
                if is_imgur_image_valid(url): links.append(url)
            else:
                links.append(url)
    return links

def get_article_list(start_date: date, end_date: date, max_pages: int, session: requests.Session) -> List[Tuple[str, date]]:
    """掃描看板列表，回傳符合日期與標題的文章清單"""
    tasks = []
    current_path = "/bbs/Beauty/index.html"
    today = date.today()
    current_year = today.year

    for i in range(max_pages):
        res = session.get(f"{PTT_BASE_URL}{current_path}")
        soup = BS(res.text, "html.parser")
        articles = soup.find_all("div", class_="r-ent")
        
        for art in articles:
            title_div = art.find("div", class_="title")
            date_div = art.find("div", class_="date")
            if not title_div.find('a'): continue
            
            title = title_div.text.strip()
            if "[正妹]" not in title or "cosplay" in title.lower(): continue
            
            # 解析日期
            m, d = map(int, date_div.text.split('/'))
            art_date = date(current_year, m, d)
            if art_date > today: art_date = art_date.replace(year=current_year - 1)
            
            if start_date <= art_date <= end_date:
                tasks.append((PTT_BASE_URL + title_div.find('a')['href'], art_date))
            
            # 提早結束掃描
            if art_date < start_date:
                logger.info(f"已掃描至日期 {art_date}，早於設定值，停止翻頁。")
                return tasks

        prev_link = soup.find("a", class_="btn wide", string="‹ 上頁")
        if not prev_link: break
        current_path = prev_link['href']
        time.sleep(0.5)
    return tasks
```
## notion_service.py
pipeline式處理的核心: 管理buffer
```
import logging
from collections import defaultdict
from datetime import date
from typing import List
from notion_client import Client

logger = logging.getLogger(__name__)

class NotionUploader:
    def __init__(self, token: str, database_id: str, chunk_size: int = 100):
        self.client = Client(auth=token)
        self.db_id = database_id
        self.chunk_size = chunk_size
        self.buffer = defaultdict(list)
        self.counters = defaultdict(int)

    def add_urls(self, target_date: date, urls: List[str]):
        self.buffer[target_date].extend(urls)
        # 每當達到 chunk_size 就處理
        while len(self.buffer[target_date]) >= self.chunk_size:
            self._upload_chunk(target_date)

    def flush_all(self):
        for target_date in list(self.buffer.keys()):
            if self.buffer[target_date]:
                self._upload_chunk(target_date)

    def _upload_chunk(self, target_date: date):
        chunk = self.buffer[target_date][:self.chunk_size]
        self.buffer[target_date] = self.buffer[target_date][self.chunk_size:]
        
        self.counters[target_date] += 1
        idx = self.counters[target_date]
        title = target_date.strftime('%Y-%m-%d') + (f" ({idx})" if idx > 1 else "")
        
        # 建立內容塊
        children = [{"object": "block", "type": "embed", "embed": {"url": u}} for u in chunk]
        
        try:
            self.client.pages.create(
                parent={"database_id": self.db_id},
                properties={
                    "名稱": {"title": [{"text": {"content": title}}]},
                    "日期": {"date": {"start": target_date.isoformat()}}
                },
                children=children
            )
            logger.info(f"✅ Notion 頁面建立成功: {title} ({len(chunk)} blocks)")
        except Exception as e:
            logger.error(f"❌ Notion 上傳失敗 [{title}]: {e}")
```
## main.py
串聯整個 Pipeline。
```
import logging.config
import concurrent.futures
import requests
from config import *
from ptt_scraper import get_article_list, fetch_post_images
from notion_service import NotionUploader

# 日誌設定
logging.config.fileConfig('logging.ini', encoding='utf-8')
logger = logging.getLogger(__name__)

def main():
    session = requests.Session()
    session.cookies.update(PTT_COOKIES)
    uploader = NotionUploader(NOTION_SECRET, DATABASE_ID, NOTION_CHUNK_SIZE)

    logger.info("1. 正在掃描 PTT 文章列表...")
    article_tasks = get_article_list(START_DATE, END_DATE, MAX_PAGE, session)
    logger.info(f"共計 {len(article_tasks)} 篇文章待處理。")

    logger.info("2. 開始平行提取圖片與流式上傳...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_date = {
            executor.submit(fetch_post_images, url, session): art_date 
            for url, art_date in article_tasks
        }

        for future in concurrent.futures.as_completed(future_to_date):
            art_date = future_to_date[future]
            try:
                urls = future.result()
                if urls:
                    # 只要拿到圖片，就丟進 uploader。緩衝區滿 100 會自動上傳。
                    uploader.add_urls(art_date, urls)
            except Exception as e:
                logger.error(f"提取失敗: {e}")

    logger.info("3. 處理剩餘緩衝區...")
    uploader.flush_all()
    logger.info("✨ 全部任務完成！")

if __name__ == "__main__":
    main()
```
# 結語&心得 Outroduction&Thoughts
之所以要從本地端爬蟲PTT圖片，是因為PTT有限制不能夠用雲端連線(從第三方工具pyptt說明文件中讀到的，自己找robot.txt沒有搜尋到具體規則所以選擇相信，且有嘗試過用github action的ubuntu模擬機未果了)，需求很特定是因為搜尋到PTT BEAUTY 批踢踢表特版看圖工具並沒有切合我的看圖習慣，用起來比較像是把ptt的view變成很適合看圖，會by標題來區分文章，一篇文章中有多少圖就看多少圖，所以希望直接整理成很多圖一次看，省的一直導覽導航操作頁面，剛好平常又日常性的會使用notion這個生產力工具，就把圖片url整理到notion上去，圖片url會有預覽可以看，最終達成我的目的，最初這個專案其實是用imgur的建立圖庫或是加入album等等的方式(有api可用)，但後來認為電腦版導覽的操作不如notion且原先本就沒有用imgur app的習慣所以選擇轉換平台。  
***
作業系統: Windows 11  
使用uv安裝和執行步驟:  
1. 安裝uv: 開啟powershell輸入指令
`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

    powershell -ExecutionPolicy ByPass: 允許腳本用 ByPass 執行策略忽略安全性限制執行。

    irm https://astral.sh/uv/install.ps1: irm 是 Invoke-RestMethod 的簡寫，從指定的 URL 下載腳本檔案的內容。https://astral.sh/uv/install.ps1 是 UV 官方提供的 Windows 安裝腳本。

    | iex: | 是一個管道符號，將前一個指令（下載腳本）的結果傳遞給下一個指令。iex 是 Invoke-Expression 的簡寫，會執行接收到的腳本內容。

    這段指令執行完會跳提示看要不要把uv加到環境變數中(optional)
2. 重啟終端機後執行指令: `uv sync`

    uv sync指令會讀取uv.lock檔案(which 依照pyproject.toml的定義管理間接依賴和構建虛擬環境等)
3. 在路徑建立.env資料夾並加入notion資料庫資訊:
    NOTION_SECRET= "Notion Integration Token (須注意只會生成一次，並且該Integration要先在Notion的Database中"連接"這個選項中先加入)"
    DATABASE_ID= "Notion Database ID(通常用瀏覽器開啟並取url中 "notion.so/" 後面的字串就是了)"
4. 在config.py中設定最多爬取的分頁數(預設為100因為notion一頁最多放100個url)以及要爬蟲的起訖日
5. 執行程式by 執行指令: `uv run main.py`

    uv run會尋找路徑中的虛擬環境並使用虛擬環境執行程式；  
    如果找不到接著會找pyproject.toml或是requirements.txt並建立一個虛擬環境安裝其中套件並在執行完畢後清掉虛擬環境；  
    最後如果都沒有才會在系統環境執行程式
