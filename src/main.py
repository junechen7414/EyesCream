import logging
import logging.config
import concurrent.futures
import requests

logging.config.fileConfig('../logging.ini', encoding='utf-8')
logger = logging.getLogger(__name__)

from config import START_DATE, END_DATE, MAX_PAGE, NOTION_SECRET, DATABASE_ID, NOTION_CHUNK_SIZE, PTT_COOKIES
from notion_service import NotionUploader
from ptt_scraper import scan_ptt_index, fetch_and_extract_links

def main():
    if not NOTION_SECRET or not DATABASE_ID:
        logger.error("環境變數缺少 NOTION_SECRET 或 DATABASE_ID，請檢查 .env 檔案")
        return

    logger.info("初始化 Notion 上傳器與 Request Session...")
    uploader = NotionUploader(token=NOTION_SECRET, database_id=DATABASE_ID, chunk_size=NOTION_CHUNK_SIZE)
    
    session = requests.Session()
    session.cookies.update(PTT_COOKIES)

    # 1. 先快速掃描目錄，取得待爬取的文章清單 (這步驟很快，不需流式處理)
    logger.info(f"開始掃描 {START_DATE} 到 {END_DATE} 的文章列表...")
    tasks = scan_ptt_index(START_DATE, END_DATE, MAX_PAGE, session)
    logger.info(f"掃描完成，共收集到 {len(tasks)} 篇文章。開始並行提取與流式上傳...")

    # 2. 透過 ThreadPoolExecutor 解析文章，並實作流式處理 (Streaming)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 將所有文章送入執行緒池
        future_to_task = {
            executor.submit(fetch_and_extract_links, post_url, session): (post_url, article_date)
            for post_url, article_date in tasks
        }

        # as_completed 只要有任何一個執行緒完成，就會立刻 yield 出來
        for future in concurrent.futures.as_completed(future_to_task):
            post_url, article_date = future_to_task[future]
            try:
                image_urls = future.result()
                if image_urls:
                    # ✅ 流式傳輸：一解析完圖片，馬上丟進上傳器的緩衝區
                    # 如果緩衝區剛好滿 100 張，uploader 內部會自動觸發 Notion API 上傳
                    uploader.add_urls(article_date, image_urls)
            except Exception as exc:
                logger.error(f'處理文章 {post_url} 時產生未預期錯誤: {exc}')

    # 3. 所有文章都爬取完畢後，把緩衝區剩下未滿 100 張的圖片也送出
    uploader.flush_all()
    logger.info("🎉 所有流式爬取與上傳操作已順利完成！")

if __name__ == "__main__":
    main()