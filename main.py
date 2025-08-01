from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes import pdf_processing
from logging_config import setup_logging
import logging
import os
import traceback
import sys
from config import settings

setup_logging()
logger = logging.getLogger(__name__)
logger.info("TEST: Logging system operational")

app = FastAPI(
    title="Wasslago Translation API", 
    description="PDF Translation API with OCR and YOLO",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global exception handler for better error tracking
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__,
            "endpoint": str(request.url)
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Wasslago Translation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint that reports system status"""
    try:
        yolo_model_available = os.path.exists(settings.yolo_text_classification)
        poppler_available = os.path.exists(os.path.join(settings.poppler_path, "pdftoppm"))
        
        # Check directory permissions and contents
        temp_exists = os.path.exists(settings.temp_folder)
        doc_exists = os.path.exists(settings.doc_folder)
        save_exists = os.path.exists(settings.save_dir)
        
        return {
            "status": "healthy",
            "yolo_model_available": yolo_model_available,
            "yolo_model_path": settings.yolo_text_classification,
            "poppler_available": poppler_available,
            "poppler_path": settings.poppler_path,
            "temp_folder": settings.temp_folder,
            "temp_exists": temp_exists,
            "doc_folder": settings.doc_folder,
            "doc_exists": doc_exists,
            "save_dir": settings.save_dir,
            "save_exists": save_exists,
            "environment": os.getenv("ENVIRONMENT", "production"),
            "gemini_api_configured": bool(os.getenv("GEMINI_API_KEY")),
            "python_version": sys.version
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "type": type(e).__name__
            }
        )

# Debug endpoint for translation issues
@app.get("/debug/translation")
async def debug_translation():
    """Debug endpoint to test translation components"""
    try:
        debug_info = {
            "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY")),
            "gemini_api_key_length": len(os.getenv("GEMINI_API_KEY", "")),
            "services_available": {},
            "dependencies_check": {}
        }
        
        # Test import of critical modules
        try:
            from services.translation import GoogleGeminiTranslator
            debug_info["services_available"]["translator"] = True
        except Exception as e:
            debug_info["services_available"]["translator"] = f"Error: {str(e)}"
        
        try:
            from services.pipeline import process_pdf_pipeline
            debug_info["services_available"]["pipeline"] = True
        except Exception as e:
            debug_info["services_available"]["pipeline"] = f"Error: {str(e)}"
        
        # Test critical dependencies
        try:
            import google.generativeai as genai
            debug_info["dependencies_check"]["google_generativeai"] = True
        except Exception as e:
            debug_info["dependencies_check"]["google_generativeai"] = f"Error: {str(e)}"
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Debug translation failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        )

# Configure CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",           # Local development
        "http://localhost:3001",           # Alternative local port
        "http://localhost:8080",           # Local development alternative
        "https://wasslago.com",            # Production domain
        "https://www.wasslago.com",        # With www subdomain
        "https://wasslago-fastapi-app.jollysmoke-af0b6177.eastus.azurecontainerapps.io"  # API domain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(pdf_processing.router, prefix="/api", tags=["PDF Processing"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
