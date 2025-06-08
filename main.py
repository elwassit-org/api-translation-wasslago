print("STARTING main.py")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from config import settings
from logging_config import setup_logging
from routes.pdf_processing import router as pdf_router

# Setup logging using logging_config
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Translation API",
    description="FastAPI service for PDF document translation with real-time processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS configuration
allowed_origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://localhost:8000",
    "https://localhost:8000",
]

# Add Azure App Service hostname if available
website_hostname = os.getenv("WEBSITE_HOSTNAME")
if website_hostname:
    allowed_origins.extend([
        f"https://{website_hostname}",
        f"http://{website_hostname}"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include PDF processing router
app.include_router(pdf_router, prefix="/api/pdf", tags=["pdf"])

# Core API endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Translation API is running",
        "status": "healthy",
        "environment": os.getenv("WEBSITE_SITE_NAME", "local"),
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check for Azure App Service"""
    return {
        "status": "healthy", 
        "environment": "azure" if os.getenv("WEBSITE_SITE_NAME") else "local",
        "poppler_available": check_poppler_availability()
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "api": "Translation API",
        "version": "1.0.0",
        "status": "operational",
        "features": ["pdf_processing", "websockets", "real_time_translation"]
    }

def check_poppler_availability():
    """Check if poppler-utils is available"""
    try:
        import subprocess
        result = subprocess.run(['pdfinfo', '-v'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001)) # Changed default port to 8001
    uvicorn.run(app, host="127.0.0.1", port=port)


