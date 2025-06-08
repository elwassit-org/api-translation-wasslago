# Translation API - Azure Deployment

This is a **deployment-ready branch** containing only the FastAPI translation service for Azure deployment.

## 🚀 Quick Deploy to Azure

This branch contains a complete, standalone FastAPI application optimized for Azure App Service deployment.

### Features

- **PDF Document Translation** using YOLO + Gemini AI
- **Real-time WebSocket Updates**
- **Azure-optimized Configuration**
- **Poppler PDF Processing** with automatic installation
- **Auto-scaling Ready**

### Deployment Options

#### Option 1: Azure Portal (Recommended)

1. Fork/download this repository
2. Go to [Azure Portal](https://portal.azure.com)
3. Create a new **Web App** with **Python 3.11** runtime
4. Deploy via **Local Git** or **GitHub**
5. Configure environment variables in **Configuration**

#### Option 2: Automated Scripts

```bash
# Linux/Mac/WSL
chmod +x deploy-azure.sh
./deploy-azure.sh

# Windows PowerShell
.\deploy-azure.ps1
```

### Required Environment Variables

```
GEMINI_API_KEY=your_gemini_api_key_here
```

### File Structure

```
├── main.py                 # FastAPI application
├── config.py              # Configuration settings
├── azure_config.py        # Azure environment detection
├── startup.sh             # Azure startup script
├── requirements.txt       # Python dependencies
├── runtime.txt            # Python version
├── routes/                # API endpoints
├── services/              # Business logic
├── utils/                 # Utility functions
└── README-AZURE.md        # Detailed deployment guide
```

### Dependencies Included

- **FastAPI** - Web framework
- **Gunicorn** - WSGI server for Azure
- **pdf2image** - PDF processing
- **YOLO (Ultralytics)** - Text detection
- **EasyOCR** - Optical character recognition
- **Google Generative AI** - Translation service
- **Poppler** - Auto-installed on Azure

### API Endpoints

- `GET /health` - Health check
- `POST /process-pdf/` - PDF translation
- `WebSocket /ws/{user_id}` - Real-time updates

### Azure Optimizations

✅ **Poppler Auto-Install** - Automatically installs PDF dependencies  
✅ **Environment Detection** - Adapts paths for Azure vs local  
✅ **Optimized Dependencies** - Lightweight packages for faster deployment  
✅ **Health Monitoring** - Built-in health checks for Azure  
✅ **CORS Configuration** - Ready for cross-origin requests  
✅ **Logging** - Structured logging for Azure monitoring

For detailed deployment instructions, see [README-AZURE.md](README-AZURE.md)
