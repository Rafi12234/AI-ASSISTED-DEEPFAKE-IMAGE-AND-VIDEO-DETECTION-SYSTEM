@echo off
cd /d "D:\All Projects\Deepfake-Detection-System\Deepfake-Detection-System\backend"
call .\.venv\Scripts\activate.bat
python -m app.workers.analysis_worker
pause