from fastapi import FastAPI

app = FastAPI(
    title="Deepfake Detection API",
    description="AI-assisted deepfake image and video detection backend",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "Deepfake Detection API is running"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "backend"
    }