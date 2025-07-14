#!/bin/bash
# Azure Cloud Shell Deployment Script (Bash version)
# Run this in Azure Cloud Shell for better network connectivity

# Variables - Update these with your values
RESOURCE_GROUP="wasslago-rg"
LOCATION="East US"
ACR_NAME="wasslagoacr"
APP_NAME="wasslago-api"
CONTAINER_APP_ENV="wasslago-env"

echo "=== Azure Container Deployment Script ==="

# Step 1: Check Azure login
echo "Step 1: Checking Azure login..."
az account show --output table

# Step 2: Create Resource Group
echo "Step 2: Creating Resource Group..."
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Step 3: Create Azure Container Registry
echo "Step 3: Creating Azure Container Registry..."
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --sku Basic --admin-enabled true

# Step 4: Get ACR login server
echo "Step 4: Getting ACR login server..."
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "loginServer" --output tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"

# Step 5: Build and push using ACR Tasks
echo "Step 5: Building and pushing image using ACR Tasks..."
az acr build --registry $ACR_NAME --image "${APP_NAME}:latest" --file Dockerfile.resilient .

# Step 6: Create Container Apps Environment
echo "Step 6: Creating Container Apps Environment..."
az containerapp env create --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --location "$LOCATION"

# Step 7: Get ACR password
echo "Step 7: Getting ACR credentials..."
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)

# Step 8: Create Container App
echo "Step 8: Creating Container App..."
az containerapp create \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image "${ACR_LOGIN_SERVER}/${APP_NAME}:latest" \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password $ACR_PASSWORD \
    --target-port 8000 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 10 \
    --cpu 1.0 \
    --memory 2.0Gi \
    --env-vars "PYTHONPATH=/app" "POPPLER_PATH=/usr/bin" "TEMP_FOLDER=/app/temp" "DOC_FOLDER=/app/doc" "SAVE_DIR=/app/translated"

# Step 9: Get the app URL
echo "Step 9: Getting application URL..."
APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" --output tsv)

echo "=== Deployment Complete! ==="
echo "Your API is available at: https://$APP_URL"
echo "Health check: https://$APP_URL/health"
echo "API docs: https://$APP_URL/docs"
