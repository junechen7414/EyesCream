# import library
import requests
from bs4 import BeautifulSoup as BS
import time
import sys # 導入 sys 模組用於 sys.exit()
from config import PTT_BASE_URL, PTT_COOKIES, IMAGE_BLACKLIST
from datetime import datetime, date # 確保導入了 datetime 和 date
import concurrent.futures # 導入 concurrent.futures 模組
from typing import Dict, List, Optional, Tuple


def is_imgur_image_valid(url: str) -> bool:
    """
    檢查 Imgur 圖片 URL 是否有效。

    判斷邏輯：
    - 使用 HEAD 請求追蹤重定向，檢查最終 URL。
    - 否則，判斷為有效圖片。
    - 任何請求相關錯誤都視為圖片無效。

    Args:
        url (str): Imgur 圖片的 URL。

    Returns:
        bool: 如果圖片有效則返回 True，否則返回 False。
    """
    headers = {
        "User-Agent": "your agent try google my user agent in a browser",
    }

    try:
        # 使用 HEAD 請求並允許追蹤重定向
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        response.raise_for_status() # 如果最終狀態碼是 4xx/5xx 會拋出異常

        final_url = response.url

        # 判斷最終 URL 是否導向 Imgur 首頁或 removed.png
        if final_url == "https://imgur.com/" or final_url == "https://i.imgur.com/" or final_url == "https://i.imgur.com/removed.png":
            return False

        # 如果沒有拋出異常且沒有導向首頁或無效頁面，則判斷為有效圖片
        return True

    except requests.exceptions.RequestException:
        # 處理所有請求相關錯誤 (如網路連接問題、超時、DNS 錯誤、4xx/5xx 等)
        return False
    except Exception:
        # 處理其他未預期的錯誤
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
        # 根據 PTT 日期格式 'm/d' 進行解析，月份前不補零
        parsed_date = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d").date()
        # 如果解析出的日期在未來，表示這篇文章是去年的
        if parsed_date > current_date:
            return parsed_date.replace(year=current_year - 1)
        return parsed_date
    except ValueError:
        # 如果解析失敗，返回 None
        return None

def process_article_metadata(article_html: BS, current_year: int, current_date: date) -> Optional[Tuple[str, date]]:
    """從文章列表的一項 HTML 中解析出 URL 和日期。"""
    date_div = article_html.find("div", class_="date")
    title_div = article_html.find("div", class_="title")
    
    # 確保標題和日期區塊存在，且標題中有連結
    if not date_div or not title_div or not title_div.find('a'):
        return None

    title = title_div.text.strip()
    # 篩選標題：必須包含 [正妹]，且不包含 cosplay (不分大小寫)
    if "[正妹]" not in title or "cosplay" in title.lower():
        return None

    # 解析文章日期
    article_date = parse_ptt_date(date_div.text.strip(), current_year, current_date)
    if not article_date:
        print(f"無法解析文章日期: {date_div.text.strip()}")
        return None
        
    post_url = PTT_BASE_URL + title_div.find('a').get('href')
    return post_url, article_date


# --- 主要爬蟲函式 ---

def scrape_ptt_images(start_date: date, end_date: date, max_pages: int, workers: int = 10) -> Dict[date, List[str]]:
    """
    爬取 PTT Beauty 板指定日期區間內包含 '[正妹]' 標題的文章圖片。

    Args:
        start_date (date): 爬取的開始日期。
        end_date (date): 爬取的結束日期。
        max_pages (int): 最多往回爬取的頁數上限。
        workers (int): 並行處理文章的執行緒數量。

    Returns:
        Dict[date, List[str]]: 一個字典，鍵為日期，值為該日期的所有圖片 URL 列表。
        
    Raises:
        ValueError: 如果日期設定不正確。
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

    # 3. 遍歷頁面
    for page_num in range(max_pages):
        full_url = f"{PTT_BASE_URL}{current_sub_url}"
        print(f"正在爬取第 {page_num + 1} 頁: {full_url}")

        try:
            response = session.get(full_url)
            response.raise_for_status() # 檢查請求是否成功 (e.g., 404, 500)
        except requests.RequestException as e:
            print(f"無法獲取頁面 {full_url}: {e}")
            break # 如果無法獲取頁面，則停止爬取

        bs = BS(response.text, "html.parser")
        articles_html = bs.find_all("div", class_="r-ent")

        if not articles_html:
            print("頁面未找到文章，停止爬取。")
            break

        # 4. 收集本頁面符合日期區間的文章任務
        article_tasks = []
        for article_html in articles_html:
            # 解析文章元數據 (URL, 日期)
            processed_data = process_article_metadata(article_html, current_year, today)
            if processed_data:
                post_url, article_date = processed_data
                # 檢查文章日期是否在目標範圍內
                if start_date <= article_date <= end_date:
                    article_tasks.append((post_url, article_date))

        # 5. 並行抓取圖片連結
        if article_tasks:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                # 建立 future 物件，將任務提交給執行緒池
                future_to_task = {
                    # 將 session 物件傳遞給 ExtractImages
                    executor.submit(ExtractImages, post_url, session): (post_url, article_date) 
                    for post_url, article_date in article_tasks
                }
                # 收集並行處理的結果
                for future in concurrent.futures.as_completed(future_to_task):
                    post_url, article_date_obj = future_to_task[future]
                    try:
                        image_urls = future.result()
                        if image_urls:
                            # 將圖片 URL 加入對應日期的列表
                            if article_date_obj not in images_by_date:
                                images_by_date[article_date_obj] = []
                            images_by_date[article_date_obj].extend(image_urls)
                    except Exception as exc:
                        print(f'從文章 {post_url} 提取圖片時產生錯誤: {exc}')

        # 6. 判斷是否需要提前停止
        # PTT 頁面越上方的文章越舊
        oldest_article_on_page = articles_html[0] 
        date_div = oldest_article_on_page.find("div", class_="date")
        if date_div:
            oldest_date_on_page = parse_ptt_date(date_div.text.strip(), current_year, today)
            # 如果本頁最舊的文章已經早於我們的開始日期，就沒必要再往前翻頁了
            if oldest_date_on_page and oldest_date_on_page < start_date:
                print(f"本頁最舊文章日期 {oldest_date_on_page} 早于開始日期 {start_date}，完成爬取。")
                break
        
        # 7. 尋找上一頁的連結
        next_page_link = bs.find("a", class_="btn wide", string="‹ 上頁")
        if not next_page_link or 'href' not in next_page_link.attrs:
            print("已達看板最末頁，停止爬取。")
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


def FindNextPage(bs):
    links = bs.find_all("a", attrs={"class": "btn wide"})
    for link in links:
        if link.text == "‹ 上頁":
            return link.attrs["href"]
    return None # 如果找不到連結則回傳 None

# 設定黑名單，所有包含這些字串的網址都會被過濾掉
BLACKLIST = IMAGE_BLACKLIST

def ExtractImages(url: str, session: requests.Session) -> List[str]:
    """從指定的文章 URL 中提取所有有效的圖片連結。"""
    print(f"正在處理文章: {url}")
    try:
        # 使用傳入的 session 物件發送請求
        web = session.get(url)
        web.raise_for_status() # 檢查 HTTP 狀態碼

        soup = BS(web.text, "html.parser")
        main_content = soup.find('div', id='main-content')

        links = []
        if not main_content:
            return links

        # 1. 收集所有潛在的連結
        potential_links = []
        for element in main_content.contents:
            if isinstance(element, str) and element.strip() == "--":
                break  # 遇到簽名檔分隔線 "--" 則停止

            if element.name == 'a' and 'href' in element.attrs:
                href = element['href']
                if not any(blacklisted in href for blacklisted in BLACKLIST):
                    potential_links.append(href)

        # 2. 並行驗證 Imgur 連結並收集其他連結
        valid_links = []
        imgur_tasks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {}
            for link in potential_links:
                if "imgur.com" in link:
                    future_to_url[executor.submit(is_imgur_image_valid, link)] = link
                else:
                    # 非 Imgur 連結直接視為有效
                    valid_links.append(link)

            for future in concurrent.futures.as_completed(future_to_url):
                imgur_url = future_to_url[future]
                try:
                    if future.result():
                        valid_links.append(imgur_url)
                except Exception as exc:
                    print(f"驗證 Imgur 連結 {imgur_url} 時出錯: {exc}")
        
        print(f"從 {url} 提取到 {len(valid_links)} 個有效圖片連結")
        return valid_links

    except requests.exceptions.RequestException as e:
        print(f"請求文章 {url} 失敗: {e}")
        return []
    except Exception as e:
        print(f"處理文章 {url} 時發生未知錯誤: {e}")
        return []