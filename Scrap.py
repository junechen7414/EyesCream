# import library
import json 
import requests 
from bs4 import BeautifulSoup as BS 
import time
from config import PTT_BASE_URL, PTT_COOKIES, IMAGE_BLACKLIST, get_yesterday_date
 
def Main(): 
    # 設定URL
    base_url = PTT_BASE_URL 
    sub_url = f"/bbs/Beauty/index.html" 
    cookies = PTT_COOKIES
    session = requests.Session()

    
    # 使用config中的函數獲取昨天日期
    yesterday = get_yesterday_date()

    # 指定日期，但又懶得從today開始改再計算yesterday
    # yesterday = datetime.datetime(2024, 2, 9)
    yesterday_str = f"{yesterday.month}/{yesterday.day:02d}"
    
    # 初始化變數用來記錄爬取的文章和總爬取的頁數
    data = list()
    page_count = 0
    max_page = 8
    
    while page_count < max_page:  # 設定最多爬幾頁避免無限循環
        full_url = f"{base_url}{sub_url}" # 組合URL
        
        response = session.get(full_url, cookies={'over18': '1'}) # 設定網站的cookie確認成年
        bs = BS(response.text, "html.parser") # BeautifulSoup解析網頁
        
        # 找出所有文章列表項目
        articles = bs.find_all("div", class_="r-ent")
        # 文章列表中找出今天的文章
        for article in articles:
            date = article.find("div", class_="date").text.strip()
            title_div = article.find("div", class_="title")
            
            if date == yesterday_str:  # 找到今天的文章                               
                title = title_div.text.strip()
                if "Cosplay" in title or "帥哥" in title:
                    continue
                parsed_title = SplitTitle(title)
                if parsed_title is None:
                    continue

                title_link = title_div.find('a') # 找到文章連結
                if title_link:
                    post_url = base_url + title_link.get('href')
                    images = ExtractImages(post_url, cookies, session)
                    parsed_title["Images"] = images                                       

                if parsed_title:
                    data.append(parsed_title)
        
        # 找下一頁的連結
        next_page = FindNextPage(bs)
        if not next_page:  # 如果沒有下一頁就結束
            break
        
        sub_url = next_page  # 更新 sub_url 為下一頁的網址
        page_count += 1
    
    image_urls = []
    for article in data:
        if "Images" in article:
            image_urls.extend(article["Images"])
    return image_urls

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
    try:
        web = session.get(url, cookies=cookies)
        time.sleep(1)

        if web.status_code == 429:
            time.sleep(int(web.headers.get('Retry-After', 60)))
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
                    continue

                links.append(href)

        return links

    except requests.exceptions.TooManyRedirects:
        print(f"重定向過多: {url}")
        return []  # 返回空列表，表示沒有獲取到圖片
 
if __name__ == "__main__": 
    urls = Main()
    print(f"找到{len(urls)} 張圖片")