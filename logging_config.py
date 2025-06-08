# config.py
import logging
from pathlib import Path

def setup_logging():
    """Configure logging for the entire application"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(log_dir / "app.log")  # File output
        ]
    )

    # Third-party library loggers
    for lib in ['paddleocr', 'yolo', 'pdfminer']:
        logging.getLogger(lib).setLevel(logging.WARNING)