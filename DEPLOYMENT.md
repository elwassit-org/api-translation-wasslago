# Azure Container Apps Deployment Guide

This guide explains how to deploy the Translation API to Azure Container Apps using the recommended approach with Azure Blob Storage for YOLO model management.

## Architecture Overview

- **Docker Container**: Linux-based container with Python 3.12
- **Poppler**: Installed via `apt-get` (Linux package)
- **YOLO Model**: Downloaded from Azure Blob Storage at startup
- **Managed Identity**: Used for secure access to Azure services

## Prerequisites

1. Azure CLI installed and configured
2. Docker installed
3. Azure subscription with appropriate permissions

## Step-by-Step Deployment

### 1. Build and Test Locally (Optional)

```bash
# Build the Docker image
docker build -t wasslago-api:latest .

# Test locally with environment variables
docker run -p 8000:8000 \
  -e AZURE_STORAGE_ACCOUNT_NAME=your-storage-account \
  -e GEMINI_API_KEY=your-api-key \
  wasslago-api:latest
```

### 2. Create Azure Resources

#### Using Azure Portal:

1. **Resource Group**: `translation-api-rg`
2. **Container Registry**: `translationapiacr` (unique name)
3. **Storage Account**: `translationstorage{unique}`
4. **Key Vault**: `translation-kv-{unique}`
5. **Container Apps Environment**: `translation-app-env`

#### Using Azure CLI:

```bash
# Set variables
RESOURCE_GROUP="translation-api-rg"
LOCATION="East US"
ACR_NAME="translationapiacr"
STORAGE_ACCOUNT="translationstorage$RANDOM"
KEY_VAULT="translation-kv-$RANDOM"
CONTAINER_APP_ENV="translation-app-env"
CONTAINER_APP="wasslago-translation-api"

# Create resource group
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Create container registry
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location "$LOCATION" \
  --sku Standard_LRS

# Create blob container for models
az storage container create \
  --name models \
  --account-name $STORAGE_ACCOUNT

# Create key vault
az keyvault create \
  --name $KEY_VAULT \
  --resource-group $RESOURCE_GROUP \
  --location "$LOCATION"

# Create Container Apps environment
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location "$LOCATION"
```

### 3. Upload YOLO Model to Blob Storage

```bash
# Upload your YOLO model file
az storage blob upload \
  --account-name $STORAGE_ACCOUNT \
  --container-name models \
  --name yolov11x_best.pt \
  --file ./models/yolov11x_best.pt
```

### 4. Set Secrets in Key Vault

```bash
# Add Gemini API key
az keyvault secret set \
  --vault-name $KEY_VAULT \
  --name "gemini-api-key" \
  --value "YOUR_GEMINI_API_KEY"
```

### 5. Build and Push Docker Image

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Get ACR login server
ACR_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)

# Build and tag image
docker build -t $ACR_SERVER/wasslago-api:latest .

# Push image
docker push $ACR_SERVER/wasslago-api:latest
```

### 6. Deploy Container App

```bash
# Create container app
az containerapp create \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image $ACR_SERVER/wasslago-api:latest \
  --registry-server $ACR_SERVER \
  --registry-username $(az acr credential show --name $ACR_NAME --query username --output tsv) \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv) \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars \
    TEMP_FOLDER="/app/temp" \
    DOC_FOLDER="/app/doc" \
    SAVE_DIR="/app/translated" \
    POPPLER_PATH="/usr/bin" \
    YOLO_MODEL_PATH="/app/models/yolov11x_best.pt" \
    AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT" \
    AZURE_STORAGE_CONTAINER_NAME="models" \
    YOLO_MODEL_BLOB_NAME="yolov11x_best.pt"
```

### 7. Configure Managed Identity and Permissions

```bash
# Enable system-assigned managed identity
az containerapp identity assign \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --system-assigned

# Get the principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query principalId --output tsv)

# Grant storage blob data reader role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Storage Blob Data Reader" \
  --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

# Grant Key Vault secrets user role
az role assignment create \
  --assignee $PRINCIPAL_ID \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/$KEY_VAULT"
```

### 8. Add Key Vault Secret Reference

```bash
# Update container app to use Key Vault secret
az containerapp update \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars GEMINI_API_KEY="secretref:gemini-api-key" \
  --secrets gemini-api-key="keyvaultref:https://$KEY_VAULT.vault.azure.net/secrets/gemini-api-key,identityref:system"
```

### 9. Test Deployment

```bash
# Get the application URL
APP_URL=$(az containerapp show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn --output tsv)

# Test health endpoint
curl https://$APP_URL/health

# Test the API
curl -X POST https://$APP_URL/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_lang": "en", "target_lang": "fr"}'
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `TEMP_FOLDER` | Temporary files directory | `/app/temp` |
| `DOC_FOLDER` | Document processing directory | `/app/doc` |
| `SAVE_DIR` | Translated files output directory | `/app/translated` |
| `POPPLER_PATH` | Poppler binaries path | `/usr/bin` |
| `YOLO_MODEL_PATH` | Local YOLO model file path | `/app/models/yolov11x_best.pt` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | `translationstorage123` |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container name | `models` |
| `YOLO_MODEL_BLOB_NAME` | YOLO model blob name | `yolov11x_best.pt` |
| `GEMINI_API_KEY` | Google Gemini API key | `secretref:gemini-api-key` |

## Monitoring and Troubleshooting

### View Logs
```bash
az containerapp logs show \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --follow
```

### Scale Application
```bash
az containerapp update \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 5
```

### Update Image
```bash
# Build new image
docker build -t $ACR_SERVER/wasslago-api:v2 .
docker push $ACR_SERVER/wasslago-api:v2

# Update container app
az containerapp update \
  --name $CONTAINER_APP \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_SERVER/wasslago-api:v2
```

## CI/CD Integration

For automated deployments, consider setting up GitHub Actions or Azure DevOps pipelines using the Azure Developer CLI (`azd`) with the provided `azure.yaml` configuration.

```bash
# Initialize azd project
azd init

# Deploy using azd
azd up
```
