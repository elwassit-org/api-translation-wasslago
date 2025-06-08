# Azure Deployment Script for Translation API (PowerShell)
# Run this script to deploy the FastAPI application to Azure App Service

param(
    [string]$ResourceGroup = "translation-api-rg",
    [string]$AppServicePlan = "translation-api-plan", 
    [string]$Location = "East US",
    [string]$Runtime = "PYTHON|3.11"
)

# Generate unique app name
$AppName = "translation-api-$(Get-Date -Format 'yyyyMMddHHmmss')"

Write-Host "Starting Azure deployment for Translation API..." -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroup"
Write-Host "App Service Plan: $AppServicePlan"
Write-Host "App Name: $AppName"
Write-Host "Location: $Location"

# Check if Azure CLI is installed
try {
    az --version | Out-Null
} catch {
    Write-Host "Azure CLI is not installed. Please install it first." -ForegroundColor Red
    Write-Host "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check Azure login status
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
try {
    az account show | Out-Null
} catch {
    Write-Host "Please login to Azure..." -ForegroundColor Yellow
    az login
}

# Create resource group
Write-Host "Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# Create App Service plan
Write-Host "Creating App Service plan..." -ForegroundColor Yellow
az appservice plan create `
    --name $AppServicePlan `
    --resource-group $ResourceGroup `
    --location $Location `
    --is-linux `
    --sku B1

# Create the web app
Write-Host "Creating web app..." -ForegroundColor Yellow
az webapp create `
    --name $AppName `
    --resource-group $ResourceGroup `
    --plan $AppServicePlan `
    --runtime $Runtime

# Configure startup command
Write-Host "Configuring startup command..." -ForegroundColor Yellow
az webapp config set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --startup-file startup.sh

# Set environment variables
Write-Host "Setting environment variables..." -ForegroundColor Yellow
az webapp config appsettings set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --settings `
        PYTHONPATH="/home/site/wwwroot" `
        FASTAPI_ENV="production" `
        LOGGING_LEVEL="INFO" `
        SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# Deploy the application
Write-Host "Deploying application..." -ForegroundColor Yellow
az webapp up `
    --name $AppName `
    --resource-group $ResourceGroup `
    --plan $AppServicePlan `
    --location $Location `
    --runtime $Runtime

Write-Host ""
Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "App URL: https://$AppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Set your GEMINI_API_KEY in the Azure portal:"
Write-Host "   az webapp config appsettings set --name $AppName --resource-group $ResourceGroup --settings GEMINI_API_KEY=your_key_here"
Write-Host ""
Write-Host "2. Upload your YOLO model to the models directory"
Write-Host ""
Write-Host "3. Update your Next.js app to use this API endpoint:"
Write-Host "   https://$AppName.azurewebsites.net/api"
Write-Host ""
Write-Host "4. Add your Next.js app URL to allowed CORS origins in main.py"
