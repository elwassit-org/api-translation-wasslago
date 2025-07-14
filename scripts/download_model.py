#!/usr/bin/env python3
"""
Azure Model Download Script
Downloads YOLO model from Azure Blob Storage before starting the application
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_model_from_azure() -> bool:
    """
    Download YOLO model from Azure Blob Storage
    Returns True if successful, False otherwise
    """
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.identity import DefaultAzureCredential
        
        # Get environment variables
        storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'models')
        blob_name = os.getenv('YOLO_MODEL_BLOB_NAME', 'yolov11x_best.pt')
        local_path = os.getenv('YOLO_MODEL_PATH', '/app/models/yolov11x_best.pt')
        
        # Validate required environment variables
        if not storage_account:
            logger.warning("AZURE_STORAGE_ACCOUNT_NAME not set, skipping Azure model download")
            return False
            
        # Create local directory if it doesn't exist
        local_dir = Path(local_path).parent
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if model already exists
        if os.path.exists(local_path):
            logger.info(f"Model already exists at {local_path}")
            return True
            
        logger.info(f"Downloading YOLO model from Azure Storage...")
        logger.info(f"Storage Account: {storage_account}")
        logger.info(f"Container: {container_name}")
        logger.info(f"Blob: {blob_name}")
        logger.info(f"Local Path: {local_path}")
        
        # Create blob service client using managed identity
        account_url = f"https://{storage_account}.blob.core.windows.net"
        credential = DefaultAzureCredential()
        
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential
        )
        
        # Download the blob
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Download with progress indication
        logger.info("Starting download...")
        with open(local_path, "wb") as download_file:
            blob_data = blob_client.download_blob()
            download_file.write(blob_data.readall())
            
        # Verify download
        if os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            logger.info(f"Model downloaded successfully to {local_path} ({file_size} bytes)")
            return True
        else:
            logger.error("Download completed but file not found")
            return False
            
    except ImportError as e:
        logger.error(f"Azure libraries not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading model from Azure: {e}")
        return False

def download_model_from_url() -> bool:
    """
    Fallback: Download a default YOLO model from public URL
    Returns True if successful, False otherwise
    """
    try:
        import requests
        
        local_path = os.getenv('YOLO_MODEL_PATH', '/app/models/yolov11x_best.pt')
        fallback_url = os.getenv('YOLO_MODEL_FALLBACK_URL', 
                                'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt')
        
        # Create local directory if it doesn't exist
        local_dir = Path(local_path).parent
        local_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if model already exists
        if os.path.exists(local_path):
            logger.info(f"Model already exists at {local_path}")
            return True
            
        logger.info(f"Downloading fallback YOLO model from {fallback_url}")
        
        response = requests.get(fallback_url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            logger.info(f"Fallback model downloaded successfully to {local_path} ({file_size} bytes)")
            return True
        else:
            logger.error("Fallback download completed but file not found")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading fallback model: {e}")
        return False

def ensure_model_available() -> bool:
    """
    Ensure YOLO model is available, trying Azure first, then fallback
    Returns True if model is available, False otherwise
    """
    # Try Azure download first
    if download_model_from_azure():
        return True
        
    # Fallback to public model download
    logger.info("Azure download failed or not configured, trying fallback download...")
    if download_model_from_url():
        return True
        
    # If both fail, check if a model already exists
    local_path = os.getenv('YOLO_MODEL_PATH', '/app/models/yolov11x_best.pt')
    if os.path.exists(local_path):
        logger.info(f"Using existing model at {local_path}")
        return True
        
    logger.error("No YOLO model available - application may not function correctly")
    return False

if __name__ == "__main__":
    success = ensure_model_available()
    if not success:
        logger.warning("Model download failed, but continuing startup...")
        # Don't exit with error to allow app to start
        # The application should handle missing models gracefully
    
    logger.info("Model setup completed")
