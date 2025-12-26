# 說明 / Introduction
之所以從本地端爬蟲PTT圖片，是因為PTT有限制不能夠用雲端連線(從第三方工具pyptt說明文件中讀到的，自己找robot.txt沒什麼結果選擇相信)，選擇一個日期區間並僅限標題內容包含"正妹"且同時標題內容不包含"Cosplay"(personal preference)的文章把圖片蒐集起來上傳到個人的notion資料庫中。  
***
作業系統: Windows 11  
使用uv安裝和執行步驟:  
1. 安裝uv: 開啟powershell輸入指令
`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

    powershell -ExecutionPolicy ByPass: 允許腳本用 ByPass 執行策略忽略安全性限制執行。

    irm https://astral.sh/uv/install.ps1: irm 是 Invoke-RestMethod 的簡寫，從指定的 URL 下載腳本檔案的內容。https://astral.sh/uv/install.ps1 是 UV 官方提供的 Windows 安裝腳本。

    | iex: | 是一個管道符號，將前一個指令（下載腳本）的結果傳遞給下一個指令。iex 是 Invoke-Expression 的簡寫，會執行接收到的腳本內容。

    這段指令執行完會跳提示看要不要把uv加到環境變數中(optional)
2. 重啟終端機後執行指令: `uv sync`

    uv sync指令會讀取uv.lock檔案(which 依照pyproject.toml的定義管理間接依賴和構建虛擬環境等)
3. 在路徑建立.env資料夾並加入notion資料庫資訊:
    NOTION_SECRET= "Notion Integration Token (須注意只會生成一次，並且該Integration要先在Notion的Database中"連接"這個選項中先加入)"
    DATABASE_ID= "Notion Database ID(通常用瀏覽器開啟並取url中 "notion.so/" 後面的字串就是了)"
4. 在shareConstant.py中設定最多爬取的分頁數(預設為100)以及開始和結束日期
5. 執行程式by 執行指令: `uv run notionPageCreate.py`

    uv run會尋找路徑中的虛擬環境並使用虛擬環境執行程式；  
    如果找不到接著會找pyproject.toml或是requirements.txt並建立一個虛擬環境安裝其中套件並在執行完畢後清掉虛擬環境；  
    最後如果都沒有才會在系統環境執行程式
