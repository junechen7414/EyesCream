# import library
import requests 
from bs4 import BeautifulSoup as BS 
import time
from config import PTT_BASE_URL, PTT_COOKIES, IMAGE_BLACKLIST, get_date_range, MAX_PAGE
from datetime import datetime # Import datetime here
 
def Main(): 
    # 設定URL
    base_url = PTT_BASE_URL 
    sub_url = f"/bbs/Beauty/index.html" 
    cookies = PTT_COOKIES
    session = requests.Session()

    
    # 使用config中的函數獲取日期區間
    date_range = get_date_range()
    
    # 使用字典來儲存按日期分組的圖片連結
    images_by_date = {}
    
    for target_date in date_range:
        target_date_str = f"{target_date.month}/{target_date.day:02d}"
        page_count = 0
        max_page = MAX_PAGE # 設定最多爬幾頁避免無限循環
        current_sub_url = sub_url # 重置 sub_url 為每一天

        # 初始化當前目標日期的圖片列表
        if target_date not in images_by_date:
            images_by_date[target_date] = []

        while page_count < max_page:  
            full_url = f"{base_url}{current_sub_url}" # 組合URL
            
            response = session.get(full_url, cookies=cookies) # 設定網站的cookie確認成年
            bs = BS(response.text, "html.parser") # BeautifulSoup解析網頁
            
            # 找出所有文章列表項目
            articles = bs.find_all("div", class_="r-ent")
            
            # 文章列表中找出目標日期的文章
            for article in articles:
                date = article.find("div", class_="date").text.strip()
                title_div = article.find("div", class_="title")
                
                if date == target_date_str:  # 找到目標日期的文章                               
                    title = title_div.text.strip()
                    if "Cosplay" in title or "帥哥" in title or "神人" in title or "公告" in title:
                        continue
                    parsed_title = SplitTitle(title)
                    if parsed_title is None:
                        continue

                    title_link = title_div.find('a') # 找到文章連結
                    if title_link:
                        post_url = base_url + title_link.get('href')
                        images = ExtractImages(post_url, cookies, session)
                        # 將圖片連結加入到對應日期的列表中
                        images_by_date[target_date].extend(images)                                       

            # 找下一頁的連結
            next_page = FindNextPage(bs)
            if not next_page:  # 如果沒有下一頁就結束
                break
            
            current_sub_url = next_page  # 更新 current_sub_url 為下一頁的網址
            page_count += 1
        
    # 回傳按日期分組的圖片連結字典
    return images_by_date

def SplitTitle(title: str): 
    if "本文已被刪除" in title: 
        return 
    if "[" not in title: 
        return 
    if "]" not in title: 
        return 
 
    r = title.index("]") 
 
    title = title[r + 1 :].strip() 
 
    return {"Title": title} 
 
 
def FindNextPage(bs): 
    links = bs.find_all("a", attrs={"class": "btn wide"}) 
    for link in links: 
        if link.text == "‹ 上頁": 
            return link.attrs["href"] 

# 設定黑名單，所有包含這些字串的網址都會被過濾掉
BLACKLIST = IMAGE_BLACKLIST

def ExtractImages(url, cookies, session):
    print(f"Processing URL: {url}") 
    try:
        web = session.get(url, cookies=cookies)
        
        time.sleep(1)
        

        if web.status_code == 429:
            retry_after = int(web.headers.get('Retry-After', 60))
            print(f"Received 429 status code. Retrying after {retry_after} seconds.") 
            
            time.sleep(retry_after)
            
            web = session.get(url, cookies=cookies)

        soup = BS(web.text, "html.parser")
        main_content = soup.find('div', id='main-content')

        links = []
        for element in main_content.contents:  # 遍歷所有子節點 (包括 #text)
            if isinstance(element, str) and element.strip() == "--":
                break  # 遇到 "--" 則停止

            if element.name == 'a' and 'href' in element.attrs:
                href = element['href']
                

                # 黑名單過濾: 如果網址包含黑名單中的關鍵字，就跳過
                if any(blacklisted in href for blacklisted in BLACKLIST):
                    print(f"Skipping blacklisted link: {href}") 
                    continue

                links.append(href)
        print(f"Extracted {len(links)} images from {url}") 
        return links

    except requests.exceptions.TooManyRedirects:
        print(f"Too many redirects for URL: {url}") 
        return []  # 返回空列表，表示沒有獲取到圖片
 
if __name__ == "__main__": 
    # 在這裡執行時，仍然會印出所有圖片的總數，但Main函式回傳的是字典
    images_data = Main()
    total_images = sum(len(urls) for urls in images_data.values())
    print(f"找到{total_images} 張圖片")