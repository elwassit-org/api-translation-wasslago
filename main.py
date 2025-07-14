from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import pdf_processing
from logging_config import setup_logging
import logging
import os
from config import settings

setup_logging()
logging.getLogger(__name__).info("TEST: Logging system operational")

app = FastAPI(title="Translation API", description="PDF Translation API with OCR and YOLO")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint that reports system status"""
    yolo_model_available = os.path.exists(settings.yolo_text_classification)
    poppler_available = os.path.exists(os.path.join(settings.poppler_path, "pdftoppm"))
    
    return {
        "status": "healthy",
        "yolo_model_available": yolo_model_available,
        "yolo_model_path": settings.yolo_text_classification,
        "poppler_available": poppler_available,
        "poppler_path": settings.poppler_path,
        "temp_folder": settings.temp_folder,
        "doc_folder": settings.doc_folder,
        "save_dir": settings.save_dir
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_processing.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
