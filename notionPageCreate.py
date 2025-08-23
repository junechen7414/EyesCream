from notion_client import Client
import concurrent.futures
from config import (
    NOTION_SECRET,
    DATABASE_ID,
    NOTION_CHUNK_SIZE,
    START_DATE,      # 匯入開始日期
    END_DATE,        # 匯入結束日期
    MAX_PAGE         # 匯入最大頁數
)
from Scraper import scrape_ptt_images
import logging
import logging.config # 1. 匯入 logging.config

# --- 設定日誌 ---
# 2. 移除舊的 basicConfig，改用 fileConfig 讀取設定檔
logging.config.fileConfig('logging.ini',encoding='utf-8')

# 3. 取得一個 logger 實例，推薦用 __name__ 當作名稱
logger = logging.getLogger(__name__)

notion = Client(auth=NOTION_SECRET)

# 修改建立頁面的邏輯為函數
def create_notion_page(page_title, date_value):
    properties = {
        "名稱": {
            "title": [
                {
                    "text": {
                        "content": page_title
                    }
                }
            ]
        },
        "日期": {
            "date": {
                "start": date_value.isoformat()
            }
        }
    }

    parent = {"database_id": DATABASE_ID}
    try:
        return notion.pages.create(parent=parent, properties=properties)
    except Exception as e:
        # 將 logging.error 改為 logger.error
        logger.error(f"建立 Notion 頁面 '{page_title}' 失敗: {e}")
        return None

# 處理圖片URL的主要邏輯
# 獲取按日期分組的圖片連結字典
# 直接在頂層呼叫匯入的函式，並傳入必要的參數
def main():
    """主執行函式"""
    try:
        logger.info("開始從 PTT 爬取圖片資料...")
        images_by_date = scrape_ptt_images(
            start_date=START_DATE, 
            end_date=END_DATE, 
            max_pages=MAX_PAGE
        )
        logger.info("資料爬取完成。")
    except ValueError as e:
        logger.error(f"[設定錯誤] {e}")
        return # 如果日期設定錯誤，直接結束程式

    chunk_size = NOTION_CHUNK_SIZE  # Notion的URL限制

    # 定義一個函式來處理單一頁面的建立與更新
    def process_page_creation(date, chunk_urls, page_index):
        page_title = f"{date.strftime('%Y-%m-%d')}" if page_index == 1 else f"{date.strftime('%Y-%m-%d')} {page_index}"
        
        new_page = create_notion_page(page_title, date)
        if not new_page:
            return # 如果頁面建立失敗，則跳過後續操作

        page_id = new_page['id']
        logger.info(f"成功建立頁面 {page_title}，Page ID: {page_id}")

        try:
            children_blocks = [{"object": "block", "type": "embed", "embed": {"url": url}} for url in chunk_urls]
            notion.blocks.children.append(block_id=page_id, children=children_blocks)
            logger.info(f"成功更新頁面 {page_title} 的內容")
        except Exception as e:
            logger.error(f"更新頁面 {page_title} 內容時發生錯誤: {e}")

    # 使用 ThreadPoolExecutor 來並行處理所有頁面
    logger.info("開始建立 Notion 頁面...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor: # Notion API 有速率限制，max_workers 不宜過高
        futures = []
    # 遍歷每個日期及其圖片列表
        for date, image_urls in images_by_date.items():
            if not image_urls:
                logger.info(f"日期 {date.strftime('%Y-%m-%d')} 沒有找到圖片，跳過建立頁面。")
                continue

            # 將URLs分組處理
            for i in range(0, len(image_urls), chunk_size):
                chunk_urls = image_urls[i:i+chunk_size]
                page_index = (i // chunk_size) + 1
                futures.append(executor.submit(process_page_creation, date, chunk_urls, page_index))

            # 等待所有任務完成
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result() # 檢查是否有異常拋出
            except Exception as e:
                logger.error(f"執行緒池任務發生錯誤: {e}")

    logger.info("全部操作完成！請檢查您的 Notion 日曆。")

if __name__ == "__main__":
    main()