#!/usr/bin/env python3
"""
Development server startup script with proper Python path configuration
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path to resolve imports
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Also add parent directories that might be needed
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print(f"🔧 Added to Python path: {current_dir}")
print(f"🔧 Current working directory: {os.getcwd()}")

# Now import and run the application
try:
    import uvicorn
    from main import app
    
    print("✅ Successfully imported main application")
    print("🚀 Starting FastAPI development server...")
    print("📝 Server will be available at: http://127.0.0.1:8000")
    print("📚 API documentation will be available at: http://127.0.0.1:8000/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Start the server
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(current_dir)],
        log_level="info"
    )
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure all required dependencies are installed:")
    print("   pip install fastapi uvicorn python-multipart python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting server: {e}")
    sys.exit(1)
