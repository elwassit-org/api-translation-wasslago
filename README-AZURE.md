# Translation API - Azure Deployment

This FastAPI application provides PDF document translation services using YOLO models and Gemini AI.

## Prerequisites

1. **Azure CLI** - [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **Azure Account** - Active Azure subscription
3. **Gemini API Key** - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
4. **YOLO Model** - Trained YOLO model file (`yolov11x_best.pt`)

## Quick Deployment

### Option 1: Automated Deployment Script

**For Linux/Mac/WSL:**

```bash
chmod +x deploy-azure.sh
./deploy-azure.sh
```

**For Windows PowerShell:**

```powershell
.\deploy-azure.ps1
```

### Option 2: Manual Deployment

1. **Login to Azure:**

   ```bash
   az login
   ```

2. **Create Resource Group:**

   ```bash
   az group create --name translation-api-rg --location "East US"
   ```

3. **Create App Service Plan:**

   ```bash
   az appservice plan create \
     --name translation-api-plan \
     --resource-group translation-api-rg \
     --location "East US" \
     --is-linux \
     --sku B1
   ```

4. **Create Web App:**

   ```bash
   az webapp create \
     --name your-translation-api \
     --resource-group translation-api-rg \
     --plan translation-api-plan \
     --runtime "PYTHON|3.11"
   ```

5. **Deploy Code:**
   ```bash
   az webapp up \
     --name your-translation-api \
     --resource-group translation-api-rg
   ```

## Post-Deployment Configuration

### 1. Set Environment Variables

```bash
az webapp config appsettings set \
  --name your-translation-api \
  --resource-group translation-api-rg \
  --settings \
    GEMINI_API_KEY="your_gemini_api_key_here"
```

### 2. Upload YOLO Model

Upload your trained YOLO model (`yolov11x_best.pt`) to the `/home/site/wwwroot/models/` directory in Azure App Service:

**Option A: Using Azure CLI**

```bash
az webapp deploy \
  --name your-translation-api \
  --resource-group translation-api-rg \
  --src-path ./models/yolov11x_best.pt \
  --target-path /home/site/wwwroot/models/yolov11x_best.pt \
  --type static
```

**Option B: Using Kudu/SCM**

1. Go to `https://your-translation-api.scm.azurewebsites.net`
2. Navigate to Debug Console > CMD
3. Go to `site/wwwroot/models/`
4. Upload your model file

### 3. Configure CORS for Your Next.js App

Update the `allowed_origins` list in `main.py` to include your Next.js application URL:

```python
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://your-nextjs-app.vercel.app",  # Your deployed Next.js app
]
```

## File Structure

```
api-translation-documents/
├── main.py                 # FastAPI application entry point
├── azure_config.py         # Azure environment configuration
├── config.py              # Application settings
├── requirements.txt       # Python dependencies (Azure-optimized)
├── startup.sh             # Azure App Service startup script
├── runtime.txt            # Python runtime version
├── .deployment            # Azure deployment configuration
├── azure.env.template     # Environment variables template
├── deploy-azure.sh        # Linux/Mac deployment script
├── deploy-azure.ps1       # Windows PowerShell deployment script
├── routes/                # API routes
├── services/              # Business logic services
└── models/                # YOLO model files (upload after deployment)
```

## Environment Configuration

The application automatically detects Azure environment and adjusts paths accordingly:

- **Local Development**: Uses Windows/Linux paths from `.env`
- **Azure App Service**: Uses Linux paths optimized for Azure

### Key Environment Differences:

| Setting     | Local (Windows)                                | Azure App Service           |
| ----------- | ---------------------------------------------- | --------------------------- |
| Poppler     | `C:\Program Files\poppler-24.08.0\Library\bin` | `/usr/bin`                  |
| Temp Folder | `./tmp`                                        | `/tmp/app_temp`             |
| Documents   | `./doc`                                        | `/home/site/wwwroot/doc`    |
| Models      | `./models`                                     | `/home/site/wwwroot/models` |

## API Endpoints

Once deployed, your API will be available at:

- **Base URL**: `https://your-app-name.azurewebsites.net`
- **Health Check**: `GET /health`
- **Process PDF**: `POST /api/process-pdf/`
- **WebSocket**: `WS /api/ws/{user_id}`

## Updating Your Next.js App

Update your Next.js application to use the Azure API endpoint:

```typescript
// In your Next.js app
const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "https://your-translation-api.azurewebsites.net/api"
    : "http://localhost:8000/api";
```

## Monitoring and Logs

### View Application Logs:

```bash
az webapp log tail --name your-translation-api --resource-group translation-api-rg
```

### Enable Application Insights:

```bash
az webapp log config --name your-translation-api --resource-group translation-api-rg --application-logging filesystem
```

## Troubleshooting

### Common Issues:

1. **Startup Fails**: Check logs with `az webapp log tail`
2. **Model Not Found**: Ensure YOLO model is uploaded to `/home/site/wwwroot/models/`
3. **CORS Errors**: Add your frontend URL to `allowed_origins` in `main.py`
4. **Dependencies**: Check `requirements.txt` and ensure all packages are compatible

### Debug Commands:

```bash
# Check app status
az webapp show --name your-translation-api --resource-group translation-api-rg

# View configuration
az webapp config show --name your-translation-api --resource-group translation-api-rg

# Restart app
az webapp restart --name your-translation-api --resource-group translation-api-rg
```

## Cost Optimization

- **B1 Plan**: ~$13.14/month for basic workloads
- **Scale Up**: Upgrade to S1 for better performance if needed
- **Scale Down**: Use F1 (free tier) for development/testing

## Security

- API keys are stored as environment variables
- CORS is configured for specific origins
- Uses Azure App Service built-in security features

## Support

For issues with:

- **Azure Deployment**: Check Azure documentation
- **API Functionality**: Review application logs
- **Model Performance**: Ensure YOLO model is properly trained and uploaded
