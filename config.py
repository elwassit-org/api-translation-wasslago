from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path
import os
from azure_config import azure_config
 
load_dotenv()

class Settings(BaseSettings):
    # Environment-aware paths
    doc_folder: str = azure_config.get_doc_folder()
    temp_folder: str = azure_config.get_temp_folder()
    save_dir: str = azure_config.get_save_dir()
    poppler_path: str = azure_config.get_poppler_path()
      # Model and API settings
    yolo_text_classification: str = os.getenv("YOLO_TEXT_CLASSIFICATION", 
        azure_config.get_yolo_model_path())
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # Azure deployment settings (optional)
    azure_env_name: str = ""
    azure_location: str = ""
    azure_subscription_id: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields instead of raising errors

# Initialize settings
settings = Settings()

# Ensure required folders exist using Azure-aware config
azure_config.ensure_directories_exist()

# Log environment info for debugging
import logging
logger = logging.getLogger(__name__)
logger.info(f"Environment configuration: {azure_config.get_environment_info()}")


