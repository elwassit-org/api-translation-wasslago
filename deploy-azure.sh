#!/bin/bash

# Azure Deployment Script for Translation API
# Run this script to deploy the FastAPI application to Azure App Service

set -e

# Configuration
RESOURCE_GROUP="translation-api-rg"
APP_SERVICE_PLAN="translation-api-plan"
APP_NAME="translation-api-$(date +%s)"  # Add timestamp for uniqueness
LOCATION="East US"
RUNTIME="PYTHON|3.11"

echo "Starting Azure deployment for Translation API..."
echo "Resource Group: $RESOURCE_GROUP"
echo "App Service Plan: $APP_SERVICE_PLAN" 
echo "App Name: $APP_NAME"
echo "Location: $LOCATION"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install it first."
    echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Login to Azure (if not already logged in)
echo "Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "Please login to Azure..."
    az login
fi

# Create resource group
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Create App Service plan (Linux, B1 tier)
echo "Creating App Service plan..."
az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --location "$LOCATION" \
    --is-linux \
    --sku B1

# Create the web app
echo "Creating web app..."
az webapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --runtime "$RUNTIME"

# Configure startup command
echo "Configuring startup command..."
az webapp config set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file startup.sh

# Set environment variables
echo "Setting environment variables..."
az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        PYTHONPATH="/home/site/wwwroot" \
        FASTAPI_ENV="production" \
        LOGGING_LEVEL="INFO" \
        SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# Deploy the application
echo "Deploying application..."
az webapp up \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --location "$LOCATION" \
    --runtime "$RUNTIME"

echo ""
echo "Deployment completed successfully!"
echo ""
echo "App URL: https://$APP_NAME.azurewebsites.net"
echo ""
echo "Next steps:"
echo "1. Set your GEMINI_API_KEY in the Azure portal:"
echo "   az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP --settings GEMINI_API_KEY=your_key_here"
echo ""
echo "2. Upload your YOLO model to the models directory"
echo ""
echo "3. Update your Next.js app to use this API endpoint:"
echo "   https://$APP_NAME.azurewebsites.net/api"
echo ""
echo "4. Add your Next.js app URL to allowed CORS origins in main.py"
