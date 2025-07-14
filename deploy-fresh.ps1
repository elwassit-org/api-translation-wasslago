# Azure deployment script for FastAPI Wasslago Translation API

param(
    [string]$ResourceGroupName = "rg-wasslago-fastapi",
    [string]$Location = "eastus",
    [string]$AppName = "wasslago-fastapi-app",
    [string]$AcrName = "acrwasslago$(Get-Random -Minimum 1000 -Maximum 9999)",
    [string]$ImageName = "wasslago-fastapi",
    [string]$ImageTag = "latest"
)

Write-Host "🚀 Starting Fresh Azure Deployment for Wasslago FastAPI" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Yellow

# Check if Azure CLI is logged in
Write-Host "📋 Checking Azure CLI authentication..." -ForegroundColor Blue
try {
    $account = az account show --query "name" -o tsv 2>$null
    if (-not $account) {
        throw "Not logged in"
    }
    Write-Host "✅ Logged in to Azure account: $account" -ForegroundColor Green
} catch {
    Write-Host "❌ Please login to Azure CLI first: az login" -ForegroundColor Red
    exit 1
}

# Set subscription (optional - uses default)
Write-Host "📋 Using Azure subscription..." -ForegroundColor Blue
$subscription = az account show --query "name" -o tsv
Write-Host "✅ Using subscription: $subscription" -ForegroundColor Green

# Create Resource Group
Write-Host "📦 Creating Resource Group: $ResourceGroupName" -ForegroundColor Blue
az group create --name $ResourceGroupName --location $Location --query "properties.provisioningState" -o tsv
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Resource Group created successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create Resource Group" -ForegroundColor Red
    exit 1
}

# Create Azure Container Registry
Write-Host "🐳 Creating Azure Container Registry: $AcrName" -ForegroundColor Blue
az acr create --resource-group $ResourceGroupName --name $AcrName --sku Basic --admin-enabled true --query "provisioningState" -o tsv
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container Registry created successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create Container Registry" -ForegroundColor Red
    exit 1
}

# Get ACR login server
$acrLoginServer = az acr show --name $AcrName --resource-group $ResourceGroupName --query "loginServer" -o tsv
Write-Host "🔑 ACR Login Server: $acrLoginServer" -ForegroundColor Cyan

# Build and push Docker image
Write-Host "🏗️ Building Docker image..." -ForegroundColor Blue
$fullImageName = "$acrLoginServer/$ImageName" + ":" + $ImageTag
Write-Host "📦 Building image: $fullImageName" -ForegroundColor Cyan
docker build -f Dockerfile.production -t $fullImageName .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image built successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to build Docker image" -ForegroundColor Red
    exit 1
}

# Login to ACR
Write-Host "🔐 Logging into Azure Container Registry..." -ForegroundColor Blue
az acr login --name $AcrName
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Logged into ACR successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to login to ACR" -ForegroundColor Red
    exit 1
}

# Push image to ACR
Write-Host "📤 Pushing image to Azure Container Registry..." -ForegroundColor Blue
docker push $fullImageName
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Image pushed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to push image" -ForegroundColor Red
    exit 1
}

# Get ACR credentials
Write-Host "🔑 Retrieving ACR credentials..." -ForegroundColor Blue
$acrUsername = az acr credential show --name $AcrName --query "username" -o tsv
$acrPassword = az acr credential show --name $AcrName --query "passwords[0].value" -o tsv

# Create Container Apps Environment
$envName = "env-$AppName"
Write-Host "🌐 Creating Container Apps Environment: $envName" -ForegroundColor Blue
az containerapp env create --name $envName --resource-group $ResourceGroupName --location $Location --query "provisioningState" -o tsv
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container Apps Environment created successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create Container Apps Environment" -ForegroundColor Red
    exit 1
}

# Create Container App
Write-Host "📱 Creating Container App: $AppName" -ForegroundColor Blue
az containerapp create `
    --name $AppName `
    --resource-group $ResourceGroupName `
    --environment $envName `
    --image $fullImageName `
    --registry-server $acrLoginServer `
    --registry-username $acrUsername `
    --registry-password $acrPassword `
    --target-port 8000 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 3 `
    --cpu 2.0 `
    --memory 4Gi `
    --env-vars GEMINI_API_KEY="AIzaSyAFrQ1RcGXsHgteXhNL6Ee3SNpZuTMICHc" YOLO_MODEL_PATH="/app/models/yolov11x_best.pt" `
    --query "properties.configuration.ingress.fqdn" -o tsv

if ($LASTEXITCODE -eq 0) {
    $appUrl = az containerapp show --name $AppName --resource-group $ResourceGroupName --query "properties.configuration.ingress.fqdn" -o tsv
    Write-Host "✅ Container App created successfully" -ForegroundColor Green
    Write-Host "🌍 App URL: https://$appUrl" -ForegroundColor Cyan
    Write-Host "🔍 Health Check: https://$appUrl/health" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to create Container App" -ForegroundColor Red
    exit 1
}

# Test the deployment
Write-Host "🧪 Testing deployment..." -ForegroundColor Blue
Start-Sleep -Seconds 30  # Wait for app to start
try {
    $response = Invoke-WebRequest -Uri "https://$appUrl/health" -UseBasicParsing -TimeoutSec 30
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Deployment test successful!" -ForegroundColor Green
        Write-Host "📊 Health check response: $($response.Content)" -ForegroundColor Cyan
    } else {
        Write-Host "⚠️ App is running but health check returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ Health check failed, but app might still be starting up" -ForegroundColor Yellow
    Write-Host "💡 Try again in a few minutes: https://$appUrl/health" -ForegroundColor Cyan
}

Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Yellow
Write-Host "📋 Deployment Summary:" -ForegroundColor Blue
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "  Container Registry: $AcrName" -ForegroundColor White
Write-Host "  Container App: $AppName" -ForegroundColor White
Write-Host "  App URL: https://$appUrl" -ForegroundColor White
Write-Host "  Health Check: https://$appUrl/health" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Yellow
