@echo off

echo Starting Docker services...
cd /d "D:\All Projects\Deepfake-Detection-System\Deepfake-Detection-System"
docker compose up -d

echo Starting Backend...
start "Deepfake Backend" cmd /k "cd /d D:\All Projects\Deepfake-Detection-System\Deepfake-Detection-System\backend && call .\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting Backend Worker...
start "Deepfake Backend Worker" cmd /k "cd /d D:\All Projects\Deepfake-Detection-System\Deepfake-Detection-System\backend && call .\.venv\Scripts\activate.bat && python -m app.workers.analysis_worker"

echo Starting AI Service...
start "Deepfake AI Service" cmd /k "cd /d D:\All Projects\Deepfake-Detection-System\Deepfake-Detection-System\ai-worker && call .\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010"

echo Starting Frontend...
start "Deepfake Frontend" cmd /k "cd /d D:\All Projects\Deepfake-Detection-System\Deepfake-Detection-System\frontend && npm run dev"

echo All services started.
pause