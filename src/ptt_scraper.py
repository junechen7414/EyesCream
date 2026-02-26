import requests
from bs4 import BeautifulSoup as BS
import time
from datetime import datetime, date
from typing import List, Tuple, Optional
import logging

from config import PTT_BASE_URL, IMAGE_BLACKLIST

logger = logging.getLogger(__name__)

INVALID_IMGUR_URLS = {
    "https://imgur.com/",
    "https://i.imgur.com/",
    "https://i.imgur.com/removed.png"
}

def is_imgur_image_valid(url: str) -> bool:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        return response.status_code == 200 and response.url not in INVALID_IMGUR_URLS
    except requests.exceptions.RequestException:
        return False

def fetch_and_extract_links(post_url: str, session: requests.Session) -> List[str]:
    """抓取單一文章並提取有效圖片連結"""
    try:
        response = session.get(post_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"請求文章失敗 {post_url}: {e}")
        return []

    soup = BS(response.text, "html.parser")
    main_content = soup.find('div', id='main-content')
    if not main_content:
        return []

    valid_links = []
    for element in main_content.contents:
        if isinstance(element, str) and "--" == element.strip():
            break 
            
        if element.name == 'a' and 'href' in element.attrs:
            href = element['href']
            if any(blacklisted in href for blacklisted in IMAGE_BLACKLIST):
                continue
                
            if "imgur.com" in href:
                if is_imgur_image_valid(href):
                    valid_links.append(href)
            else:
                valid_links.append(href)
                
    if valid_links:
        logger.debug(f"從 {post_url} 提取到 {len(valid_links)} 個連結")
    return valid_links

def scan_ptt_index(start_date: date, end_date: date, max_pages: int, session: requests.Session) -> List[Tuple[str, date]]:
    """快速掃描看板分頁，收集在日期範圍內的文章 URL"""
    article_tasks = []
    current_sub_url = "/bbs/Beauty/index.html"
    current_year = datetime.now().year
    today = date.today()

    for page_num in range(max_pages):
        full_url = f"{PTT_BASE_URL}{current_sub_url}"
        logger.info(f"正在掃描看板第 {page_num + 1} 頁: {full_url}")

        try:
            response = session.get(full_url)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"無法獲取頁面 {full_url}: {e}")
            break

        bs = BS(response.text, "html.parser")
        articles_html = bs.find_all("div", class_="r-ent")
        
        if not articles_html:
            break

        for article_html in articles_html:
            date_div = article_html.find("div", class_="date")
            title_div = article_html.find("div", class_="title")
            
            if not date_div or not title_div or not title_div.find('a'):
                continue

            title = title_div.text.strip()
            if "[正妹]" not in title or "cosplay" in title.lower():
                continue

            date_str = date_div.text.strip()
            try:
                article_date = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d").date()
                if article_date > today:
                    article_date = article_date.replace(year=current_year - 1)
            except ValueError:
                continue

            if start_date <= article_date <= end_date:
                post_url = PTT_BASE_URL + title_div.find('a').get('href')
                article_tasks.append((post_url, article_date))

        # 判斷是否需要提前停止 (檢查該頁最舊文章)
        oldest_date_str = articles_html[0].find("div", class_="date").text.strip()
        try:
            oldest_date = datetime.strptime(f"{current_year}/{oldest_date_str}", "%Y/%m/%d").date()
            if oldest_date > today:
                oldest_date = oldest_date.replace(year=current_year - 1)
            if oldest_date < start_date:
                logger.info(f"已達設定的最舊日期 {start_date}，掃描結束。")
                break
        except ValueError:
            pass

        next_page_link = bs.find("a", class_="btn wide", string="‹ 上頁")
        if not next_page_link:
            break
            
        current_sub_url = next_page_link['href']
        time.sleep(0.5)

    return article_tasks