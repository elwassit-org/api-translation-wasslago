from fastapi import FastAPI
import logging
import os

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Translation API",
    description="FastAPI service for PDF document translation",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Translation API is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": os.getenv("WEBSITE_SITE_NAME", "local"),
        "python_version": os.getenv("PYTHON_VERSION", "unknown")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
