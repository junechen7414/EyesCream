# import library
import requests
from bs4 import BeautifulSoup as BS
import time
import sys # 導入 sys 模組用於 sys.exit()
from config import PTT_BASE_URL, PTT_COOKIES, IMAGE_BLACKLIST, START_DATE, END_DATE, MAX_PAGE
from datetime import datetime, date # 確保導入了 datetime 和 date

def is_imgur_image_valid(url):
    """
    檢查給定的 Imgur 圖片 URL 是否有效。

    此函數會根據 Imgur 的特殊行為模式判斷圖片狀態：
    - 如果首次 HEAD 請求返回 200 狀態碼，則判斷為有效圖片。
    - 如果首次 HEAD 請求返回 3xx 重新導向，則追蹤最終 URL 。
      - 若最終導向至 Imgur 首頁 (imgur.com/)，則圖片無效。
      - 否則，判斷為有效圖片。
    - 如果首次 HEAD 請求返回其他非 200/3xx 狀態碼或發生網路錯誤，則判斷為無效。

    Args:
        url (str): Imgur 圖片的 URL (建議使用 i.imgur.com 開頭的直鏈)。

    Returns:
        bool: 如果圖片有效則返回 True，否則返回 False。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36",
    }

    try:
        # 首次請求，不追蹤重定向，只獲取 Header 資訊
        response = requests.head(url, headers=headers, allow_redirects=False, timeout=10)
        initial_status_code = response.status_code

        # 如果首次響應是 200，圖片通常是有效的
        if initial_status_code == 200:            
            return True

        # 如果首次響應是 3xx (重新導向)
        elif 300 <= initial_status_code < 400:
            # 追蹤所有重定向 by allow_redirects=True，檢查最終狀態
            final_response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            final_response.raise_for_status() # 如果最終狀態碼是 4xx/5xx 會拋出異常

            final_url = final_response.url            

            # 判斷最終 URL 是否導向 Imgur 首頁            
            if final_url == "https://imgur.com/" or final_url == "https://i.imgur.com/" or final_url == "https://i.imgur.com/removed.png":
                return False

            # 如果通過檢查，則判斷為有效圖片
            return True

        # 其他非 200/3xx 的狀態碼，例如 404 Not Found, 500 Internal Server Error 等
        else:
            return False

    except requests.exceptions.RequestException:
        # 處理所有請求相關錯誤 (如網路連接問題、超時、DNS 錯誤、4xx/5xx 等)
        return False
    except Exception:
        # 處理其他未預期的錯誤
        return False


# 爬蟲主要function
def scrape_ptt_images():
    # 獲取實際的當前日期
    current_actual_date = date.today()

    # 檢查 END_DATE 是否晚於實際的當前日期
    if END_DATE > current_actual_date:
        print(f"錯誤：設定的結束日期 END_DATE ({END_DATE.strftime('%Y-%m-%d')}) 晚於實際的當前日期 ({current_actual_date.strftime('%Y-%m-%d')})。")
        print("請將 END_DATE 設定為不晚於當前日期。")
        sys.exit(1) # 終止程式

    # 檢查 START_DATE 是否晚於 END_DATE
    if START_DATE > END_DATE:
        print(f"錯誤：設定的開始日期 START_DATE ({START_DATE.strftime('%Y-%m-%d')}) 晚於結束日期 END_DATE ({END_DATE.strftime('%Y-%m-%d')})。")
        print("請確保 START_DATE 不晚於 END_DATE。")
        sys.exit(1) # 終止程式

    # 設定URL
    base_url = PTT_BASE_URL
    sub_url = f"/bbs/Beauty/index.html" # 從最新頁面開始
    cookies = PTT_COOKIES
    session = requests.Session() # 使用 session 保持會話和 cookie

    # 使用字典來儲存按日期分組的圖片連結
    images_by_date = {}

    page_count = 0
    # MAX_PAGE 作為安全上限，主要停止條件是日期
    max_page_limit = MAX_PAGE
    current_sub_url = sub_url

    stop_scraping = False # 標記是否停止爬取

    # 獲取當前年份，用於解析 PTT 的 MM/DD 日期格式
    current_year = datetime.now().year
    current_date = date.today() # 獲取實際的當前日期

    # 從最新頁面開始往回爬取
    while page_count < max_page_limit:
        full_url = f"{base_url}{current_sub_url}" # 組合URL
        print(f"正在爬取頁面: {full_url}") # 增加進度提示

        response = session.get(full_url, cookies=cookies) # 設定網站的cookie確認成年
        bs = BS(response.text, "html.parser") # BeautifulSoup解析網頁

        # 找出所有文章列表項目
        articles = bs.find_all("div", class_="r-ent")

        # 如果頁面沒有文章，可能已到看板盡頭或發生錯誤，停止
        if not articles:
            print("頁面未找到文章，停止爬取。")
            break

        oldest_article_date_on_page = None # 用來記錄本頁最舊文章的日期

        # 獲取本頁最舊文章的日期 (列表中的第一篇文章)
        # 用於在處理完本頁後判斷是否應該停止
        if articles:
            first_article = articles[0] # 列表中的第一篇文章是該頁最舊的文章
            date_div = first_article.find("div", class_="date")
            if date_div:
                date_str = date_div.text.strip()
                try:
                    # 嘗試使用當前年份解析日期
                    parsed_date_this_year = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d").date()

                    # 根據解析出的日期是否晚於實際當前日期來判斷年份
                    if parsed_date_this_year > current_date:
                        # 如果解析出的日期在未來，則實際年份應為前一年
                        oldest_article_date_on_page = datetime.strptime(f"{current_year - 1}/{date_str}", "%Y/%m/%d").date()
                    else:
                        # 否則，實際年份為當前年份
                        oldest_article_date_on_page = parsed_date_this_year

                except ValueError:
                    print(f"無法解析本頁最舊文章日期: {date_str} (頁面: {full_url})")
                    # 為了安全起見，如果無法解析最舊日期，我們設定停止標記
                    stop_scraping = True # Treat unparseable date as a reason to stop


        # 遍歷頁面上的文章 (從最舊到最新)
        for article in articles:
            date_div = article.find("div", class_="date")
            title_div = article.find("div", class_="title")

            # 跳過日期或標題缺失的文章，或標題沒有連結的文章
            if not date_div or not title_div or title_div.find('a') is None:
                continue

            date_str = date_div.text.strip()

            # 解析文章日期 (PTT 日期格式為 MM/DD)
            try:
                # 嘗試使用當前年份解析日期
                parsed_date_this_year = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d").date()

                # 根據解析出的日期是否晚於實際當前日期來判斷年份
                if parsed_date_this_year > current_date:
                    # 如果解析出的日期在未來，則實際年份應為前一年
                    article_date_obj = datetime.strptime(f"{current_year - 1}/{date_str}", "%Y/%m/%d").date()
                else:
                    # 否則，實際年份為當前年份
                    article_date_obj = parsed_date_this_year

            except ValueError:
                print(f"無法解析日期: {date_str} (頁面: {full_url})")
                continue # 跳過此文章

            # 如果文章日期在目標區間 [START_DATE, END_DATE] 內，則處理
            if START_DATE <= article_date_obj <= END_DATE:
                title = title_div.text.strip()
                # 只處理標題包含 "[正妹]" 的文章，跳過其他標題
                if "[正妹]" not in title or "Cosplay" in title or "cosplay" in title:
                    continue

                title_link = title_div.find('a')
                # 再次確認有連結 (雖然上面已經檢查過)
                if title_link:
                    post_url = base_url + title_link.get('href')
                    # 調用修改後的 ExtractImages 函數，它會包含 Imgur 有效性檢查
                    images = ExtractImages(post_url, cookies, session)

                    # 將圖片連結加入到對應日期的字典中
                    # 使用 article_date_obj 作為字典的鍵
                    if article_date_obj not in images_by_date:
                        images_by_date[article_date_obj] = []
                    images_by_date[article_date_obj].extend(images)


        # 在處理完本頁所有文章後，檢查本頁最舊文章的日期
        # 如果本頁最舊文章的日期早於 START_DATE，則設定停止標記
        # 這樣可以確保本頁所有日期 >= START_DATE 的文章都被處理
        if oldest_article_date_on_page is not None and oldest_article_date_on_page < START_DATE:
            print(f"本頁最舊文章日期 {oldest_article_date_on_page.strftime('%Y-%m-%d')} 早於開始日期 {START_DATE.strftime('%Y-%m-%d')}，設定停止標記。")
            stop_scraping = True


        # 如果設置了停止標記，則跳出頁面遍歷迴圈 (在處理文章之後檢查)
        if stop_scraping:
            break

        # 尋找下一頁的連結 (即 PTT 頁面上的 "‹ 上頁" 按鈕)
        next_page = FindNextPage(bs)
        if not next_page:  # 如果找不到上一頁的連結，表示已到看板最舊頁面，結束
            print("未找到更多頁面。")
            break

        current_sub_url = next_page  # 更新 current_sub_url 為上一頁的網址
        page_count += 1
        time.sleep(1) # 在爬取不同頁面之間加入短暫延遲，避免被鎖

    # (可選) 在回傳前按日期排序結果
    # 字典的鍵 (日期) 會自動按時間順序排序
    sorted_images_by_date = dict(sorted(images_by_date.items()))

    # 回傳按日期分組的圖片連結字典
    return sorted_images_by_date


def FindNextPage(bs):
    links = bs.find_all("a", attrs={"class": "btn wide"})
    for link in links:
        if link.text == "‹ 上頁":
            return link.attrs["href"]
    return None # 如果找不到連結則回傳 None

# 設定黑名單，所有包含這些字串的網址都會被過濾掉
BLACKLIST = IMAGE_BLACKLIST

def ExtractImages(url, cookies, session):
    print(f"Processing URL: {url}")
    try:
        web = session.get(url, cookies=cookies)
        web.raise_for_status() # 檢查 HTTP 狀態碼，如果不是 200 則會拋出異常 (例如 429, 404 等)

        soup = BS(web.text, "html.parser")
        main_content = soup.find('div', id='main-content')

        links = []
        # 檢查 main_content 是否存在且有內容
        if main_content and main_content.contents:
            for element in main_content.contents:  # 遍歷所有子節點 (包括 #text)
                if isinstance(element, str) and element.strip() == "--":
                    break  # 遇到 "--" 則停止

                if element.name == 'a' and 'href' in element.attrs:
                    href = element['href']

                    # 黑名單過濾: 如果網址包含黑名單中的關鍵字，就跳過
                    if any(blacklisted in href for blacklisted in BLACKLIST):
                        print(f"Skipping blacklisted link: {href}")
                        continue
                    
                    # 判斷是否為 Imgur 連結，如果是，則額外使用 is_imgur_image_valid 進行驗證
                    if "imgur.com" in href: # 簡單判斷是否為 Imgur 連結
                        if is_imgur_image_valid(href):
                            links.append(href)
                            print(f"Validated Imgur link added: {href}")
                        else:
                            print(f"Invalid Imgur link skipped: {href}")
                    else:
                        # 對於非 Imgur 連結，直接加入 (可根據需要添加其他圖片服務的驗證)
                        links.append(href)
                        print(f"Non-Imgur link added: {href}")

        print(f"Extracted {len(links)} valid images from {url}")
        return links

    except requests.exceptions.HTTPError as e:
        # 捕獲 HTTP 錯誤 (例如 404, 429 等)
        print(f"HTTP Error for URL {url}: {e.response.status_code} - {e.response.reason}")
        # 如果是 429，您可能需要在 scrape_ptt_images 函數的層級處理，
        # 或者讓它返回空列表，並在主循環中決定是否重試該文章。
        # 這裡由於 ExtractImages 只是獲取圖片，直接返回空列表比較合理。
        return []
    except requests.exceptions.RequestException as e:
        # 捕獲其他請求錯誤
        print(f"Request Error for URL {url}: {e}")
        return []
    except Exception as e: # 捕獲其他可能的請求/解析錯誤
        print(f"An unexpected error occurred while processing {url}: {e}")
        return []