from notion_client import Client
from config import (
    NOTION_SECRET,
    DATABASE_ID,
    NOTION_CHUNK_SIZE,
    get_today_date
)

# 因為Scrap.py在同一個資料夾,可以直接import不需要加入sys.path
from Scrap import Main as get_images

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

# 獲取今天的日期
today = get_today_date()

# 若要指定日期來生成notion page
# today = datetime(2025, 2, 8)

# 處理圖片URL的主要邏輯
image_urls = get_images()
chunk_size = NOTION_CHUNK_SIZE  # Notion的URL限制

# 將URLs分組處理
for i in range(0, len(image_urls), chunk_size):
    chunk_urls = image_urls[i:i+chunk_size]
    page_index = (i // chunk_size) + 1
    page_title = "eyes cream" if page_index == 1 else f"eyes cream {page_index}"
    
    # 建立新頁面
    new_page = create_notion_page(page_title, today)
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