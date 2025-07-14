# Azure Cloud Shell Deployment Script
# Run this in Azure Cloud Shell for better network connectivity

# Variables - Update these with your values
$RESOURCE_GROUP = "wasslago-rg"
$LOCATION = "East US"
$ACR_NAME = "wasslagoacr"
$APP_NAME = "wasslago-api"
$CONTAINER_APP_ENV = "wasslago-env"

Write-Host "=== Azure Container Deployment Script ===" -ForegroundColor Green

# Step 1: Login to Azure (if not already logged in)
Write-Host "Step 1: Checking Azure login..." -ForegroundColor Yellow
az account show --output table

# Step 2: Create Resource Group
Write-Host "Step 2: Creating Resource Group..." -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION

# Step 3: Create Azure Container Registry
Write-Host "Step 3: Creating Azure Container Registry..." -ForegroundColor Yellow
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic --admin-enabled true

# Step 4: Get ACR login server
Write-Host "Step 4: Getting ACR login server..." -ForegroundColor Yellow
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "loginServer" --output tsv
Write-Host "ACR Login Server: $ACR_LOGIN_SERVER" -ForegroundColor Cyan

# Step 5: Build and push using ACR Tasks (this avoids local Docker issues)
Write-Host "Step 5: Building and pushing image using ACR Tasks..." -ForegroundColor Yellow
az acr build --registry $ACR_NAME --image "$APP_NAME`:latest" --file Dockerfile.resilient .

# Step 6: Create Container Apps Environment
Write-Host "Step 6: Creating Container Apps Environment..." -ForegroundColor Yellow
az containerapp env create --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --location $LOCATION

# Step 7: Create Container App
Write-Host "Step 7: Creating Container App..." -ForegroundColor Yellow
az containerapp create `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --environment $CONTAINER_APP_ENV `
    --image "$ACR_LOGIN_SERVER/$APP_NAME`:latest" `
    --registry-server $ACR_LOGIN_SERVER `
    --registry-username $ACR_NAME `
    --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv) `
    --target-port 8000 `
    --ingress external `
    --min-replicas 0 `
    --max-replicas 10 `
    --cpu 1.0 `
    --memory 2.0Gi `
    --env-vars "PYTHONPATH=/app" "POPPLER_PATH=/usr/bin" "TEMP_FOLDER=/app/temp" "DOC_FOLDER=/app/doc" "SAVE_DIR=/app/translated"

# Step 8: Get the app URL
Write-Host "Step 8: Getting application URL..." -ForegroundColor Yellow
$APP_URL = az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" --output tsv
Write-Host "Application URL: https://$APP_URL" -ForegroundColor Green

Write-Host "=== Deployment Complete! ===" -ForegroundColor Green
Write-Host "Your API is available at: https://$APP_URL" -ForegroundColor Cyan
Write-Host "Health check: https://$APP_URL/health" -ForegroundColor Cyan
Write-Host "API docs: https://$APP_URL/docs" -ForegroundColor Cyan
