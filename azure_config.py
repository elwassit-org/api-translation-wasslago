import os
import platform
import shutil
from pathlib import Path

class AzureConfig:
    """Configuration class to handle Azure-specific settings"""
    
    def __init__(self):
        self.is_azure = self._detect_azure_environment()
        self.is_windows = platform.system() == "Windows"
    
    def _detect_azure_environment(self) -> bool:
        """Detect if running in Azure App Service"""
        azure_indicators = [
            "WEBSITE_SITE_NAME",
            "WEBSITE_RESOURCE_GROUP", 
            "WEBSITE_HOSTNAME",
            "APPSETTING_WEBSITE_SITE_NAME"        ]
        return any(os.getenv(indicator) for indicator in azure_indicators)
    
    def get_poppler_path(self) -> str:
        """Get the appropriate Poppler path based on environment"""
        if self.is_azure:
            # Azure App Service uses Ubuntu/Linux - check multiple possible paths
            possible_paths = [
                "/usr/bin",  # Standard Ubuntu installation
                "/usr/local/bin",  # Alternative installation location
                "/opt/poppler/bin",  # Custom installation
            ]
            
            # Try to find pdftoppm executable
            pdftoppm_path = shutil.which("pdftoppm")
            if pdftoppm_path:
                return os.path.dirname(pdftoppm_path)
            
            # Fallback to first existing path
            for path in possible_paths:
                if os.path.exists(os.path.join(path, "pdftoppm")):
                    return path
            
            # Ultimate fallback for Azure
            return "/usr/bin"
        elif self.is_windows:
            # Local Windows development - check multiple sources
            # 1. Environment variable from .env
            poppler_env = os.getenv("POPPLER_PATH")
            if poppler_env and os.path.exists(poppler_env):
                return poppler_env
            
            # 2. Check project-local poppler installation
            local_poppler = "./bin/poppler-windows"
            if os.path.exists(os.path.join(local_poppler, "pdftoppm.exe")):
                return local_poppler
            
            # 3. Try to find in system PATH
            pdftoppm_path = shutil.which("pdftoppm")
            if pdftoppm_path:
                return os.path.dirname(pdftoppm_path)
            
            # 4. Common installation paths
            common_paths = [
                r"C:\Program Files\poppler-24.08.0\Library\bin",
                r"C:\Program Files\poppler\bin",
                r"C:\poppler\bin"
            ]
            for path in common_paths:
                if os.path.exists(os.path.join(path, "pdftoppm.exe")):
                    return path
            
            # Fallback - let the user know they need to install poppler
            raise FileNotFoundError(
                "Poppler not found. Please install poppler or set POPPLER_PATH in .env file"
            )
        else:
            # Local Linux/Mac development
            pdftoppm_path = shutil.which("pdftoppm")
            if pdftoppm_path:
                return os.path.dirname(pdftoppm_path)
            return "/usr/bin"
    
    def get_temp_folder(self) -> str:
        """Get the appropriate temp folder path"""
        if self.is_azure:
            # Use Azure App Service temp directory
            return "/tmp/app_temp"
        else:
            return "./tmp"
    
    def get_doc_folder(self) -> str:
        """Get the appropriate document folder path"""
        if self.is_azure:
            # Use Azure App Service local storage
            return "/home/site/wwwroot/doc"
        else:
            return "./doc"
    
    def get_save_dir(self) -> str:
        """Get the appropriate save directory path"""
        if self.is_azure:
            # Use Azure App Service local storage
            return "/home/site/wwwroot/translated"
        else:
            return "./translated"
    
    def get_models_path(self) -> str:
        """Get the appropriate models directory path"""
        if self.is_azure:
            return "/app/models"  # Changed from /home/site/wwwroot/models to /app/models for container
        else:
            return "./models"
    
    def get_yolo_model_path(self) -> str:
        """Get the full path to the YOLO model file"""
        models_dir = self.get_models_path()
        model_filename = os.getenv("YOLO_MODEL_FILENAME", "yolov11x_best.pt")
        return os.path.join(models_dir, model_filename)

    def ensure_directories_exist(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.get_temp_folder(),
            self.get_doc_folder(), 
            self.get_save_dir(),
            self.get_models_path()
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
    def get_environment_info(self) -> dict:
        """Get information about the current environment"""
        return {
            "is_azure": self.is_azure,
            "is_windows": self.is_windows,
            "platform": platform.system(),
            "poppler_path": self.get_poppler_path(),
            "temp_folder": self.get_temp_folder(),
            "doc_folder": self.get_doc_folder(),
            "save_dir": self.get_save_dir(),
            "models_path": self.get_models_path()
        }

# Global instance
azure_config = AzureConfig()
