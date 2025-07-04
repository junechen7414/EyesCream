@echo off
REM 1. 導航到你的專案目錄（可選，如果腳本需要相對路徑）
cd C:\Users\user\Downloads\EyesCream

REM 2. 激活虛擬環境（venv）
call venv\Scripts\activate.bat

REM 3. 執行 Python 爬蟲腳本
python notionPageCreate.py

REM 4. 可選：執行完後暫停（debug 時用）
pause