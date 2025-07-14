#!/bin/bash
# Azure Cloud Shell Deployment Script (Backup Option)
# Use this if local build continues to have issues

set -e

# Variables
RESOURCE_GROUP="wasslago-translation-rg"
LOCATION="eastus"
ACR_NAME="wasslagoacr"
APP_NAME="wasslago-api"
CONTAINER_APP_ENV="wasslago-env"

echo "🌟 === Azure Cloud Shell Deployment === 🌟"
echo "This script will build and deploy your FastAPI app entirely in Azure"

# Check if we're in Azure Cloud Shell
if [ -z "$AZURE_HTTP_USER_AGENT" ]; then
    echo "⚠️  This script is designed for Azure Cloud Shell"
    echo "📖 To use Azure Cloud Shell:"
    echo "   1. Go to https://shell.azure.com"
    echo "   2. Upload your project files"
    echo "   3. Run this script"
    exit 1
fi

echo "✅ Running in Azure Cloud Shell"

# Step 1: Verify Azure CLI login
echo "🔐 Step 1: Verifying Azure login..."
az account show --output table

# Step 2: Create Resource Group
echo "🏗️  Step 2: Creating Resource Group..."
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Step 3: Create Azure Container Registry
echo "📦 Step 3: Creating Azure Container Registry..."
az acr create \
    --name $ACR_NAME \
    --resource-group $RESOURCE_GROUP \
    --sku Basic \
    --admin-enabled true \
    --location "$LOCATION"

# Step 4: Get ACR details
echo "🔑 Step 4: Getting ACR details..."
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "loginServer" --output tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"

# Step 5: Create optimized Dockerfile for Azure
echo "🐳 Step 5: Creating optimized Dockerfile for Azure build..."
cat > Dockerfile.azure << 'EOF'
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    wget \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --timeout 600 --retries 10 -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/temp /app/doc /app/translated /app/models

# Create startup script
RUN echo '#!/bin/bash\n\
echo "🚀 Starting Translation API..."\n\
if [ ! -f "/app/models/yolov11x_best.pt" ]; then\n\
    echo "📥 Downloading YOLO model..."\n\
    if [ -n "$AZURE_STORAGE_ACCOUNT_NAME" ]; then\n\
        wget -O /app/models/yolov11x_best.pt \\\n\
            "https://${AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/models/yolov11x_best.pt" || \\\n\
        echo "⚠️  Running without YOLO model"\n\
    fi\n\
fi\n\
export TEMP_FOLDER="/app/temp"\n\
export DOC_FOLDER="/app/doc"\n\
export SAVE_DIR="/app/translated"\n\
export POPPLER_PATH="/usr/bin"\n\
export YOLO_MODEL_PATH="/app/models/yolov11x_best.pt"\n\
uvicorn main:app --host 0.0.0.0 --port 8000' > /app/startup.sh && \
    chmod +x /app/startup.sh

EXPOSE 8000
CMD ["/app/startup.sh"]
EOF

# Step 6: Build using ACR Tasks (builds in Azure, not locally)
echo "🏗️  Step 6: Building image using ACR Tasks..."
echo "This builds in Azure's infrastructure - much more reliable!"
az acr build \
    --registry $ACR_NAME \
    --image "${APP_NAME}:latest" \
    --file Dockerfile.azure \
    .

# Step 7: Create Container Apps Environment
echo "🌐 Step 7: Creating Container Apps Environment..."
az containerapp env create \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --location "$LOCATION"

# Step 8: Create Storage Account for YOLO model
echo "💾 Step 8: Creating Storage Account..."
STORAGE_ACCOUNT="wasslagostorage$(date +%s)"
az storage account create \
    --resource-group $RESOURCE_GROUP \
    --name $STORAGE_ACCOUNT \
    --location "$LOCATION" \
    --sku Standard_LRS

# Create container for models
az storage container create \
    --account-name $STORAGE_ACCOUNT \
    --name models \
    --public-access off

echo "📤 Upload your YOLO model with:"
echo "az storage blob upload --account-name $STORAGE_ACCOUNT --container-name models --name yolov11x_best.pt --file models/yolov11x_best.pt"

# Step 9: Create Key Vault
echo "🔐 Step 9: Creating Key Vault..."
KEY_VAULT="wasslago-kv-$(date +%s)"
az keyvault create \
    --resource-group $RESOURCE_GROUP \
    --name $KEY_VAULT \
    --location "$LOCATION"

echo "🔑 Add your Gemini API key with:"
echo "az keyvault secret set --vault-name $KEY_VAULT --name gemini-api-key --value 'YOUR_API_KEY'"

# Step 10: Deploy Container App
echo "🚀 Step 10: Deploying Container App..."
az containerapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image "${ACR_LOGIN_SERVER}/${APP_NAME}:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv) \
    --target-port 8000 \
    --ingress external \
    --cpu 2.0 \
    --memory 4.0Gi \
    --min-replicas 1 \
    --max-replicas 10 \
    --env-vars \
        TEMP_FOLDER="/app/temp" \
        DOC_FOLDER="/app/doc" \
        SAVE_DIR="/app/translated" \
        POPPLER_PATH="/usr/bin" \
        YOLO_MODEL_PATH="/app/models/yolov11x_best.pt" \
        AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT"

# Step 11: Get application URL
echo "🎉 Step 11: Getting application URL..."
APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" --output tsv)

echo ""
echo "🎉 === DEPLOYMENT COMPLETE! === 🎉"
echo ""
echo "📊 Resource Details:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Container Registry: $ACR_LOGIN_SERVER"
echo "   Storage Account: $STORAGE_ACCOUNT"
echo "   Key Vault: $KEY_VAULT"
echo ""
echo "🌐 Application URLs:"
echo "   App URL: https://$APP_URL"
echo "   Health Check: https://$APP_URL/health"
echo "   API Docs: https://$APP_URL/docs"
echo ""
echo "📝 Next Steps:"
echo "   1. Upload YOLO model to storage"
echo "   2. Add Gemini API key to Key Vault"
echo "   3. Configure managed identity for secrets access"
echo "   4. Test your API endpoints"
echo ""
echo "🎯 Your FastAPI Translation API is now live on Azure!"
