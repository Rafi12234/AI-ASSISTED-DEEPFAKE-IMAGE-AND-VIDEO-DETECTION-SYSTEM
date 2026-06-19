@echo off
cd /d "D:\All Projects\Deepfake-Detection-System\Deepfake-Detection-System\ai-worker"
call .\.venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
pause