# Complete Azure Deployment Guide for Wasslago Translation API
# Use this script after Docker build completes

param(
    [string]$ResourceGroup = "wasslago-rg",
    [string]$Location = "eastus",
    [string]$ACRName = "wasslagoacr",
    [string]$AppName = "wasslago-api",
    [string]$ContainerEnv = "wasslago-env",
    [string]$StorageAccount = "wasslagostorage",
    [string]$KeyVault = "wasslago-kv",
    [string]$ImageTag = "fixed",
    [string]$GeminiApiKey = $env:GEMINI_API_KEY
)

Write-Host "🚀 === Wasslago FastAPI Deployment to Azure === 🚀" -ForegroundColor Green
Write-Host "This script deploys your translation API with YOLO model support" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`n📋 Checking Prerequisites..." -ForegroundColor Yellow

# Check Azure CLI
try {
    $azVersion = az --version
    Write-Host "✅ Azure CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Azure CLI not found. Install from: https://aka.ms/installazurecliwindows" -ForegroundColor Red
    exit 1
}

# Check Docker
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Install Docker Desktop" -ForegroundColor Red
    exit 1
}

# Check if Docker image exists
$imageExists = docker images --format "table {{.Repository}}:{{.Tag}}" | Select-String "wasslago-api:$ImageTag"
if ($imageExists) {
    Write-Host "✅ Docker image wasslago-api:$ImageTag found" -ForegroundColor Green
} else {
    Write-Host "❌ Docker image wasslago-api:$ImageTag not found" -ForegroundColor Red
    Write-Host "Run: docker build -t wasslago-api:$ImageTag -f Dockerfile.azure-fixed ." -ForegroundColor Yellow
    exit 1
}

# Login to Azure
Write-Host "`n🔐 Logging into Azure..." -ForegroundColor Yellow
az login

# Create Resource Group
Write-Host "`n🏗️ Creating Resource Group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# Create Azure Container Registry
Write-Host "`n📦 Creating Azure Container Registry..." -ForegroundColor Yellow
az acr create `
    --resource-group $ResourceGroup `
    --name $ACRName `
    --sku Basic `
    --admin-enabled true `
    --location $Location

# Get ACR login server
$acrLoginServer = az acr show --name $ACRName --resource-group $ResourceGroup --query "loginServer" --output tsv
Write-Host "📍 ACR Login Server: $acrLoginServer" -ForegroundColor Cyan

# Login to ACR and push image
Write-Host "`n📤 Pushing Docker image to ACR..." -ForegroundColor Yellow
az acr login --name $ACRName

# Tag and push image
$acrImage = "${acrLoginServer}/wasslago-api:${ImageTag}"
docker tag "wasslago-api:$ImageTag" $acrImage
docker push $acrImage

Write-Host "✅ Image pushed to: $acrImage" -ForegroundColor Green

# Create Storage Account for YOLO model
Write-Host "`n💾 Creating Storage Account for YOLO model..." -ForegroundColor Yellow
az storage account create `
    --resource-group $ResourceGroup `
    --name $StorageAccount `
    --location $Location `
    --sku Standard_LRS

# Create blob container for models
az storage container create `
    --account-name $StorageAccount `
    --name models `
    --public-access off

Write-Host "📁 Storage container 'models' created" -ForegroundColor Green
Write-Host "📤 Upload your YOLO model with:" -ForegroundColor Yellow
Write-Host "   az storage blob upload --account-name $StorageAccount --container-name models --name yolov11x_best.pt --file models/yolov11x_best.pt" -ForegroundColor White

# Create Key Vault
Write-Host "`n🔐 Creating Key Vault..." -ForegroundColor Yellow
az keyvault create `
    --resource-group $ResourceGroup `
    --name $KeyVault `
    --location $Location

# Add Gemini API key to Key Vault
if ($GeminiApiKey) {
    Write-Host "🔑 Adding Gemini API key to Key Vault..." -ForegroundColor Yellow
    az keyvault secret set `
        --vault-name $KeyVault `
        --name "GEMINI-API-KEY" `
        --value $GeminiApiKey
    Write-Host "✅ Gemini API key stored in Key Vault" -ForegroundColor Green
} else {
    Write-Host "⚠️ Gemini API key not provided. Add it manually:" -ForegroundColor Yellow
    Write-Host "   az keyvault secret set --vault-name $KeyVault --name GEMINI-API-KEY --value 'YOUR_API_KEY'" -ForegroundColor White
}

# Install Container Apps extension
Write-Host "`n🔧 Installing Container Apps extension..." -ForegroundColor Yellow
az extension add --name containerapp --upgrade

# Register providers
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

# Create Container Apps Environment
Write-Host "`n🌐 Creating Container Apps Environment..." -ForegroundColor Yellow
az containerapp env create `
    --name $ContainerEnv `
    --resource-group $ResourceGroup `
    --location $Location

# Get ACR credentials
$acrUsername = az acr credential show --name $ACRName --query "username" --output tsv
$acrPassword = az acr credential show --name $ACRName --query "passwords[0].value" --output tsv

# Create Container App
Write-Host "`n🚀 Creating Container App..." -ForegroundColor Yellow
az containerapp create `
    --name $AppName `
    --resource-group $ResourceGroup `
    --environment $ContainerEnv `
    --image $acrImage `
    --registry-server $acrLoginServer `
    --registry-username $acrUsername `
    --registry-password $acrPassword `
    --target-port 8000 `
    --ingress external `
    --cpu 2.0 `
    --memory 4.0Gi `
    --min-replicas 1 `
    --max-replicas 10 `
    --env-vars `
        "TEMP_FOLDER=/app/temp" `
        "DOC_FOLDER=/app/doc" `
        "SAVE_DIR=/app/translated" `
        "POPPLER_PATH=/usr/bin" `
        "YOLO_MODEL_PATH=/app/models/yolov11x_best.pt" `
        "AZURE_STORAGE_ACCOUNT_NAME=$StorageAccount" `
        "AZURE_STORAGE_CONTAINER_NAME=models"

# Enable managed identity
Write-Host "`n🔐 Configuring Managed Identity..." -ForegroundColor Yellow
az containerapp identity assign `
    --name $AppName `
    --resource-group $ResourceGroup `
    --system-assigned

# Get principal ID for role assignments
$principalId = az containerapp identity show `
    --name $AppName `
    --resource-group $ResourceGroup `
    --query "principalId" --output tsv

# Grant storage permissions
Write-Host "🔑 Granting storage permissions..." -ForegroundColor Yellow
az role assignment create `
    --assignee $principalId `
    --role "Storage Blob Data Reader" `
    --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$ResourceGroup/providers/Microsoft.Storage/storageAccounts/$StorageAccount"

# Grant Key Vault permissions
Write-Host "🔑 Granting Key Vault permissions..." -ForegroundColor Yellow
az role assignment create `
    --assignee $principalId `
    --role "Key Vault Secrets User" `
    --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$ResourceGroup/providers/Microsoft.KeyVault/vaults/$KeyVault"

# Configure secrets in Container App
if ($GeminiApiKey) {
    Write-Host "🔐 Configuring secrets in Container App..." -ForegroundColor Yellow
    
    # Add Key Vault reference as secret
    az containerapp secret set `
        --name $AppName `
        --resource-group $ResourceGroup `
        --secrets "gemini-api-key=keyvaultref:https://$KeyVault.vault.azure.net/secrets/GEMINI-API-KEY,identityref:system"
    
    # Update app to use the secret
    az containerapp update `
        --name $AppName `
        --resource-group $ResourceGroup `
        --set-env-vars "GEMINI_API_KEY=secretref:gemini-api-key"
}

# Get application URL
$appUrl = az containerapp show `
    --name $AppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" --output tsv

Write-Host "`n🎉 === DEPLOYMENT COMPLETE! === 🎉" -ForegroundColor Green
Write-Host "`n📊 Deployment Summary:" -ForegroundColor Cyan
Write-Host "   Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "   Container Registry: $acrLoginServer" -ForegroundColor White
Write-Host "   Storage Account: $StorageAccount" -ForegroundColor White
Write-Host "   Key Vault: $KeyVault" -ForegroundColor White
Write-Host "   Container App: $AppName" -ForegroundColor White

Write-Host "`n🌐 Application URLs:" -ForegroundColor Cyan
Write-Host "   App URL: https://$appUrl" -ForegroundColor Green
Write-Host "   Health Check: https://$appUrl/health" -ForegroundColor Green
Write-Host "   API Documentation: https://$appUrl/docs" -ForegroundColor Green

Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Upload YOLO model to storage (command shown above)" -ForegroundColor White
Write-Host "   2. Test your API endpoints" -ForegroundColor White
Write-Host "   3. Monitor logs: az containerapp logs show --name $AppName --resource-group $ResourceGroup --follow" -ForegroundColor White
Write-Host "   4. Scale if needed: az containerapp update --name $AppName --resource-group $ResourceGroup --min-replicas 2" -ForegroundColor White

Write-Host "`n🎯 Your FastAPI Translation API with YOLO support is now live on Azure! 🎯" -ForegroundColor Green
