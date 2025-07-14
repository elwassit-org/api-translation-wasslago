#!/bin/bash

echo "🚀 Starting Translation API on Azure..."

# Set Python path
export PYTHONPATH="/root/.local/lib/python3.12/site-packages:/app"

# Print environment info
echo "📋 Environment Information:"
echo "  - Python Path: $PYTHONPATH"
echo "  - Working Directory: $(pwd)"
echo "  - User: $(whoami)"
echo "  - Poppler Path: $POPPLER_PATH"
echo "  - YOLO Model Path: $YOLO_MODEL_PATH"

# Check required directories
echo "📁 Creating required directories..."
mkdir -p "$TEMP_FOLDER" "$DOC_FOLDER" "$SAVE_DIR" "/app/models"

# Check Poppler installation
echo "🔍 Checking Poppler..."
if command -v pdftoppm &> /dev/null; then
    echo "✅ Poppler found: $(which pdftoppm)"
else
    echo "❌ Poppler not found!"
fi

# Check if Gemini API key is configured
if [ -n "$GEMINI_API_KEY" ] || [ -n "$GOOGLE_API_KEY" ]; then
    echo "✅ Gemini API key configured"
    # Ensure both environment variables are set
    if [ -n "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
        export GOOGLE_API_KEY="$GEMINI_API_KEY"
    fi
else
    echo "⚠️ No Gemini API key found"
fi

# Download YOLO model from Azure Blob Storage
echo "📥 Checking YOLO model..."
if [ ! -f "$YOLO_MODEL_PATH" ]; then
    if [ -n "$AZURE_STORAGE_ACCOUNT_NAME" ]; then
        echo "📥 Downloading YOLO model from Azure Storage..."
        python /app/scripts/download_model.py
        if [ -f "$YOLO_MODEL_PATH" ]; then
            echo "✅ YOLO model downloaded successfully"
        else
            echo "⚠️ YOLO model download failed, continuing without it"
        fi
    else
        echo "⚠️ No Azure Storage configured for YOLO model"
    fi
else
    echo "✅ YOLO model already exists"
fi

# Start the FastAPI application
echo "🌐 Starting FastAPI server..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    --access-log
