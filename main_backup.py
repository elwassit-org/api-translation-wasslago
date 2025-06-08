from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import pdf_processing
from logging_config import setup_logging
from azure_config import azure_config
import logging
import os

setup_logging()
logger = logging.getLogger(__name__)
logger.info("TEST: Logging system operational")

# Log environment information
logger.info(f"Environment: {azure_config.get_environment_info()}")

app = FastAPI(
    title="Translation API",
    description="FastAPI service for PDF document translation",
    version="1.0.0"
)

# Azure-aware CORS configuration
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://localhost:3000", # Local HTTPS
]

# Add Azure App Service hostname if available
if azure_config.is_azure:
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
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_processing.router, prefix="/api")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Translation API is running",
        "environment": azure_config.get_environment_info()
    }

@app.get("/health")
async def health_check():
    """Health check for Azure App Service"""
    return {"status": "healthy", "environment": "azure" if azure_config.is_azure else "local"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    

