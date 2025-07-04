from notion_client import Client
from config import (
    NOTION_SECRET,
    DATABASE_ID,
    NOTION_CHUNK_SIZE
)

# 因為Scraper.py在同一個資料夾,可以直接import不需要加入sys.path
# 直接匯入 scrape_ptt_images 函式
from Scraper import scrape_ptt_images

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
    return notion.pages.create(parent=parent, properties=properties)

# 處理圖片URL的主要邏輯
# 獲取按日期分組的圖片連結字典
# 直接在頂層呼叫匯入的函式
images_by_date = scrape_ptt_images()
chunk_size = NOTION_CHUNK_SIZE  # Notion的URL限制

# 遍歷每個日期及其圖片列表
for date, image_urls in images_by_date.items():
    if not image_urls:
        print(f"日期 {date.strftime('%Y-%m-%d')} 沒有找到圖片，跳過建立頁面。")
        continue

    # 將URLs分組處理
    for i in range(0, len(image_urls), chunk_size):
        chunk_urls = image_urls[i:i+chunk_size]
        page_index = (i // chunk_size) + 1
        # 使用圖片的原始發布日期作為頁面標題
        page_title = f"{date.strftime('%Y-%m-%d')}" if page_index == 1 else f"{date.strftime('%Y-%m-%d')} {page_index}"

        # 建立新頁面，使用圖片的原始發布日期
        new_page = create_notion_page(page_title, date)
        page_id = new_page['id']
        print(f"成功建立頁面 {page_title}，Page ID: {page_id}")

        # 建立當前分組的blocks
        children_blocks = [
            {
                "object": "block",
                "type": "embed",
                "embed": {
                    "url": url
                }
            }
            for url in chunk_urls
        ]

        # 更新頁面內容
        notion.blocks.children.append(
            block_id=page_id,
            children=children_blocks
        )
        print(f"成功更新頁面 {page_title} 的內容")

print("全部操作完成！請檢查您的 Notion 日曆。")