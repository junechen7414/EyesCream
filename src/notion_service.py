import logging
from collections import defaultdict
from datetime import date
from typing import List
from notion_client import Client

logger = logging.getLogger(__name__)

class NotionUploader:
    """負責管理圖片 URL 緩衝區，滿 100 筆即自動建立 Notion 頁面"""
    
    def __init__(self, token: str, database_id: str, chunk_size: int = 100):
        self.notion = Client(auth=token)
        self.database_id = database_id
        self.chunk_size = chunk_size
        
        # 緩衝區：以日期為 Key，URL 列表為 Value
        self.buffer = defaultdict(list)
        # 計數器：記錄該日期已經建立了幾個頁面，用於標題命名
        self.page_counters = defaultdict(int)

    def add_urls(self, target_date: date, urls: List[str]):
        """將新爬取到的 URL 加入緩衝區，並檢查是否需要觸發上傳"""
        self.buffer[target_date].extend(urls)
        self._process_buffer(target_date)

    def flush_all(self):
        """爬蟲結束後，將緩衝區內剩餘未滿 chunk_size 的 URL 全部上傳"""
        logger.info("準備清空並上傳所有剩餘的圖片緩衝區...")
        for target_date in list(self.buffer.keys()):
            self._process_buffer(target_date, force_flush=True)

    def _process_buffer(self, target_date: date, force_flush: bool = False):
        """處理特定日期的緩衝區"""
        while len(self.buffer[target_date]) >= self.chunk_size or (force_flush and self.buffer[target_date]):
            # 切割出要上傳的部分
            chunk = self.buffer[target_date][:self.chunk_size]
            # 留在緩衝區剩餘的部分
            self.buffer[target_date] = self.buffer[target_date][self.chunk_size:]
            
            self.page_counters[target_date] += 1
            count = self.page_counters[target_date]
            
            # 依需求設定標題：YYYY-MM-DD 或 YYYY-MM-DD (2)
            title = target_date.strftime('%Y-%m-%d')
            if count > 1:
                title += f" ({count})"
                
            self._create_page(title, target_date, chunk)

    def _create_page(self, title: str, target_date: date, urls: List[str]):
        """呼叫 Notion API 建立頁面並寫入圖片"""
        properties = {
            "名稱": {"title": [{"text": {"content": title}}]},
            "日期": {"date": {"start": target_date.isoformat()}}
        }
        # 直接在建立頁面時塞入 children，效率最高
        children_blocks = [{"object": "block", "type": "embed", "embed": {"url": url}} for url in urls]
        
        try:
            self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children_blocks
            )
            logger.info(f"✅ 成功建立 Notion 頁面 [{title}]，包含 {len(urls)} 張圖片")
        except Exception as e:
            logger.error(f"❌ 建立 Notion 頁面 [{title}] 失敗: {e}")