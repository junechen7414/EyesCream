# import library
import requests
from bs4 import BeautifulSoup as BS
import time
from config import PTT_BASE_URL, PTT_COOKIES, IMAGE_BLACKLIST
from datetime import datetime, date
import concurrent.futures
from typing import Dict, List, Optional, Tuple
import logging

# 取得此模組的 logger 實例
logger = logging.getLogger(__name__)

# --- 圖片驗證與連結提取函式 ---

def is_imgur_image_valid(url: str) -> bool:
    """
    檢查 Imgur 圖片 URL 是否有效。
    使用 HEAD 請求追蹤重定向，檢查最終 URL 是否為無效頁面。
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        response.raise_for_status()
        # 檢查最終是否導向已移除的圖片或首頁
        if response.url in ["https://imgur.com/", "https://i.imgur.com/", "https://i.imgur.com/removed.png"]:
            return False
        return True
    except requests.exceptions.RequestException:
        return False

def fetch_and_extract_links(post_url: str, session: requests.Session) -> List[str]:
    """
    (執行緒任務) 抓取單一文章頁面，解析並回傳所有有效的圖片連結。
    這個函式整合了抓取、解析、驗證的完整流程。
    """
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

    # 1. 提取所有潛在連結
    potential_links = []
    for element in main_content.contents:
        if isinstance(element, str) and element.strip() == "--":
            break  # 遇到簽名檔分隔線 "--" 則停止
        if element.name == 'a' and 'href' in element.attrs:
            href = element['href']
            # 過濾掉黑名單中的網址
            if not any(blacklisted in href for blacklisted in IMAGE_BLACKLIST):
                potential_links.append(href)

    # 2. 驗證連結並收集有效連結
    valid_links = []
    for link in potential_links:
        # 對 Imgur 連結進行有效性檢查，其他連結直接接受
        if "imgur.com" in link:
            if is_imgur_image_valid(link):
                valid_links.append(link)
        else:
            valid_links.append(link)
    
    if valid_links:
        logger.info(f"從 {post_url} 提取到 {len(valid_links)} 個有效圖片連結")
    return valid_links


# --- PTT 頁面解析輔助函式 ---

def parse_ptt_date(date_str: str, current_year: int, current_date: date) -> Optional[date]:
    """解析 PTT 的 'MM/DD' 格式日期，並處理跨年份問題。"""
    try:
        parsed_date = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d").date()
        if parsed_date > current_date:
            return parsed_date.replace(year=current_year - 1)
        return parsed_date
    except ValueError:
        return None

def process_article_metadata(article_html: BS, current_year: int, current_date: date) -> Optional[Tuple[str, date]]:
    """從文章列表的一項 HTML 中解析出 URL 和日期。"""
    date_div = article_html.find("div", class_="date")
    title_div = article_html.find("div", class_="title")
    
    if not date_div or not title_div or not title_div.find('a'):
        return None

    title = title_div.text.strip()
    if "[正妹]" not in title or "cosplay" in title.lower():
        return None

    article_date = parse_ptt_date(date_div.text.strip(), current_year, current_date)
    if not article_date:
        logger.warning(f"無法解析文章日期: {date_div.text.strip()}")
        return None
        
    post_url = PTT_BASE_URL + title_div.find('a').get('href')
    return post_url, article_date


# --- 主要爬蟲函式 ---

def scrape_ptt_images(start_date: date, end_date: date, max_pages: int, workers: int = 10) -> Dict[date, List[str]]:
    """
    爬取 PTT Beauty 板指定日期區間內包含 '[正妹]' 標題的文章圖片。
    此版本使用單一執行緒池統一管理所有文章的抓取與驗證。
    """
    # 1. 輸入驗證
    today = date.today()
    if end_date > today:
        raise ValueError(f"結束日期 {end_date} 不能晚于今天 {today}。")
    if start_date > end_date:
        raise ValueError(f"開始日期 {start_date} 不能晚于結束日期 {end_date}。")

    # 2. 初始化
    session = requests.Session()
    session.cookies.update(PTT_COOKIES)
    images_by_date: Dict[date, List[str]] = {}
    current_sub_url = "/bbs/Beauty/index.html"
    current_year = datetime.now().year

    # 3. 遍歷頁面，收集所有需要處理的文章任務
    article_tasks_to_process = []
    for page_num in range(max_pages):
        full_url = f"{PTT_BASE_URL}{current_sub_url}"
        logger.info(f"正在掃描第 {page_num + 1} 頁: {full_url}")

        try:
            response = session.get(full_url)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"無法獲取頁面 {full_url}: {e}")
            break

        bs = BS(response.text, "html.parser")
        articles_html = bs.find_all("div", class_="r-ent")
        if not articles_html:
            logger.warning("頁面未找到文章，停止掃描。")
            break

        # 收集本頁面符合日期區間的文章
        for article_html in articles_html:
            processed_data = process_article_metadata(article_html, current_year, today)
            if processed_data:
                post_url, article_date = processed_data
                if start_date <= article_date <= end_date:
                    article_tasks_to_process.append((post_url, article_date))

        # 判斷是否需要提前停止
        oldest_article_on_page = articles_html[0] 
        date_div = oldest_article_on_page.find("div", class_="date")
        if date_div:
            oldest_date_on_page = parse_ptt_date(date_div.text.strip(), current_year, today)
            if oldest_date_on_page and oldest_date_on_page < start_date:
                logger.info(f"本頁最舊文章日期 {oldest_date_on_page} 早于開始日期 {start_date}，完成掃描。")
                break
        
        # 尋找上一頁的連結
        next_page_link = bs.find("a", class_="btn wide", string="‹ 上頁")
        if not next_page_link or 'href' not in next_page_link.attrs:
            logger.info("已達看板最末頁，停止掃描。")
            break
        current_sub_url = next_page_link['href']
        time.sleep(0.5) # 減緩對 PTT 主機的請求速度

    # 4. 使用單一執行緒池，並行處理所有收集到的文章任務
    logger.info(f"掃描完成，共收集到 {len(article_tasks_to_process)} 篇文章待處理。開始提取圖片...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_task = {
            executor.submit(fetch_and_extract_links, post_url, session): (post_url, article_date) 
            for post_url, article_date in article_tasks_to_process
        }

        for future in concurrent.futures.as_completed(future_to_task):
            post_url, article_date_obj = future_to_task[future]
            try:
                image_urls = future.result()
                if image_urls:
                    if article_date_obj not in images_by_date:
                        images_by_date[article_date_obj] = []
                    images_by_date[article_date_obj].extend(image_urls)
            except Exception as exc:
                logger.error(f'處理文章 {post_url} 時產生未預期錯誤: {exc}')

    # 5. 按日期排序後回傳結果
    logger.info("所有圖片提取完成。")
    return dict(sorted(images_by_date.items()))