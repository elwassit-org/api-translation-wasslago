# Azure Translation API Complete Deployment Script
# This script creates all Azure resources and deploys the Docker image

param(
    [string]$ResourceGroupName = "rg-wasslago-api",
    [string]$Location = "East US",
    [string]$RegistryName = "acrwasslagoapi",
    [string]$StorageAccountName = "stwasslagoapi",
    [string]$KeyVaultName = "kv-wasslago-api",
    [string]$ContainerAppName = "ca-wasslago-api",
    [string]$ContainerEnvironmentName = "cae-wasslago-api",
    [string]$ImageName = "wasslago-translation-api",
    [string]$ImageTag = "latest"
)

# Color coding for output
function Write-ColorOutput($Message, $Color = "Green") {
    Write-Host $Message -ForegroundColor $Color
}

function Write-ErrorOutput($Message) {
    Write-Host $Message -ForegroundColor Red
}

function Write-WarningOutput($Message) {
    Write-Host $Message -ForegroundColor Yellow
}

Write-ColorOutput "=== Azure Translation API Deployment Starting ===" "Cyan"

# Check if Azure CLI is installed
try {
    $azVersion = az version --output tsv --query '"azure-cli"' 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI not found"
    }
    Write-ColorOutput "✓ Azure CLI version: $azVersion"
} catch {
    Write-ErrorOutput "✗ Azure CLI is not installed. Please install it first:"
    Write-ErrorOutput "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Check if logged in to Azure
try {
    $account = az account show --output json 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Not logged in"
    }
    Write-ColorOutput "✓ Logged in to Azure as: $($account.user.name)"
    Write-ColorOutput "✓ Using subscription: $($account.name) ($($account.id))"
} catch {
    Write-ErrorOutput "✗ Not logged in to Azure. Please run: az login"
    exit 1
}

# Check if Docker is running
try {
    docker info >$null 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-ColorOutput "✓ Docker is running"
} catch {
    Write-ErrorOutput "✗ Docker is not running. Please start Docker Desktop."
    exit 1
}

# Read environment variables
if (!(Test-Path ".env")) {
    Write-ErrorOutput "✗ .env file not found. Please ensure you have configured environment variables."
    exit 1
}

$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^([^#][^=]+)=(.*)$") {
        $envVars[$matches[1]] = $matches[2]
    }
}

if (!$envVars.ContainsKey("GEMINI_API_KEY") -or [string]::IsNullOrEmpty($envVars["GEMINI_API_KEY"])) {
    Write-ErrorOutput "✗ GEMINI_API_KEY not found in .env file"
    exit 1
}
Write-ColorOutput "✓ Environment variables loaded"

Write-ColorOutput "`n=== Step 1: Creating Resource Group ===" "Cyan"
try {
    az group create --name $ResourceGroupName --location $Location --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to create resource group" }
    Write-ColorOutput "✓ Resource group '$ResourceGroupName' created/updated"
} catch {
    Write-ErrorOutput "✗ Failed to create resource group: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 2: Creating Azure Container Registry ===" "Cyan"
try {
    # Create ACR
    az acr create --resource-group $ResourceGroupName --name $RegistryName --sku Basic --location $Location --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to create ACR" }
    
    # Enable admin user for easy authentication
    az acr update --name $RegistryName --admin-enabled true --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to enable ACR admin" }
    
    Write-ColorOutput "✓ Azure Container Registry '$RegistryName' created"
} catch {
    Write-ErrorOutput "✗ Failed to create ACR: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 3: Creating Storage Account ===" "Cyan"
try {
    # Create storage account
    az storage account create --resource-group $ResourceGroupName --name $StorageAccountName --location $Location --sku Standard_LRS --kind StorageV2 --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to create storage account" }
    
    # Get storage account key
    $storageKey = az storage account keys list --resource-group $ResourceGroupName --account-name $StorageAccountName --query "[0].value" --output tsv
    if ($LASTEXITCODE -ne 0) { throw "Failed to get storage key" }
    
    # Create container for YOLO model
    az storage container create --name "models" --account-name $StorageAccountName --account-key $storageKey --public-access blob --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to create storage container" }
    
    Write-ColorOutput "✓ Storage account '$StorageAccountName' created with 'models' container"
} catch {
    Write-ErrorOutput "✗ Failed to create storage account: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 4: Creating Key Vault ===" "Cyan"
try {
    # Create Key Vault
    az keyvault create --name $KeyVaultName --resource-group $ResourceGroupName --location $Location --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Key Vault" }
    
    # Store the Gemini API key
    az keyvault secret set --vault-name $KeyVaultName --name "gemini-api-key" --value $envVars["GEMINI_API_KEY"] --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to store secret" }
    
    Write-ColorOutput "✓ Key Vault '$KeyVaultName' created with Gemini API key stored"
} catch {
    Write-ErrorOutput "✗ Failed to create Key Vault: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 5: Building and Pushing Docker Image ===" "Cyan"
try {
    # Get ACR login server
    $acrLoginServer = az acr show --name $RegistryName --query loginServer --output tsv
    if ($LASTEXITCODE -ne 0) { throw "Failed to get ACR login server" }
    
    # Login to ACR
    az acr login --name $RegistryName
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to ACR" }
    
    # Build and tag the image
    $fullImageName = "$acrLoginServer/${ImageName}:${ImageTag}"
    Write-ColorOutput "Building Docker image: $fullImageName"
    docker build -f Dockerfile.azure-fixed -t $fullImageName .
    if ($LASTEXITCODE -ne 0) { throw "Failed to build Docker image" }
    
    # Push the image
    Write-ColorOutput "Pushing Docker image to ACR..."
    docker push $fullImageName
    if ($LASTEXITCODE -ne 0) { throw "Failed to push Docker image" }
    
    Write-ColorOutput "✓ Docker image built and pushed: $fullImageName"
} catch {
    Write-ErrorOutput "✗ Failed to build/push Docker image: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 6: Creating Container Apps Environment ===" "Cyan"
try {
    # Install Container Apps extension if not present
    az extension add --name containerapp --upgrade --only-show-errors
    
    # Register required providers
    az provider register --namespace Microsoft.App --only-show-errors
    az provider register --namespace Microsoft.OperationalInsights --only-show-errors
    
    # Create Container Apps environment
    az containerapp env create --name $ContainerEnvironmentName --resource-group $ResourceGroupName --location $Location --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Container Apps environment" }
    
    Write-ColorOutput "✓ Container Apps environment '$ContainerEnvironmentName' created"
} catch {
    Write-ErrorOutput "✗ Failed to create Container Apps environment: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 7: Creating Managed Identity ===" "Cyan"
try {
    # Create user-assigned managed identity
    $identityName = "id-wasslago-api"
    $identityResult = az identity create --name $identityName --resource-group $ResourceGroupName --location $Location --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Failed to create managed identity" }
    
    $principalId = $identityResult.principalId
    $clientId = $identityResult.clientId
    $identityId = $identityResult.id
    
    Write-ColorOutput "✓ Managed identity created: $identityName"
    
    # Give the identity access to Key Vault
    Start-Sleep -Seconds 30  # Wait for identity propagation
    az keyvault set-policy --name $KeyVaultName --object-id $principalId --secret-permissions get list --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to set Key Vault policy" }
    
    # Give the identity access to ACR
    $acrId = az acr show --name $RegistryName --query id --output tsv
    az role assignment create --assignee $principalId --role "AcrPull" --scope $acrId --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to assign ACR role" }
    
    # Give the identity access to Storage
    $storageId = az storage account show --name $StorageAccountName --resource-group $ResourceGroupName --query id --output tsv
    az role assignment create --assignee $principalId --role "Storage Blob Data Reader" --scope $storageId --output table
    if ($LASTEXITCODE -ne 0) { throw "Failed to assign storage role" }
    
    Write-ColorOutput "✓ Managed identity permissions configured"
} catch {
    Write-ErrorOutput "✗ Failed to create/configure managed identity: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 8: Uploading YOLO Model ===" "Cyan"
try {
    if (Test-Path "models\yolov11x_best.pt") {
        Write-ColorOutput "Uploading YOLO model to storage..."
        az storage blob upload --account-name $StorageAccountName --account-key $storageKey --container-name "models" --name "yolov11x_best.pt" --file "models\yolov11x_best.pt" --output table
        if ($LASTEXITCODE -ne 0) { throw "Failed to upload YOLO model" }
        Write-ColorOutput "✓ YOLO model uploaded to storage"
    } else {
        Write-WarningOutput "⚠ YOLO model file not found at models\yolov11x_best.pt - will download at runtime"
    }
} catch {
    Write-ErrorOutput "✗ Failed to upload YOLO model: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 9: Creating Container App ===" "Cyan"
try {
    # Get the full image name
    $fullImageName = "$acrLoginServer/${ImageName}:${ImageTag}"
    
    # Get Key Vault URI
    $keyVaultUri = az keyvault show --name $KeyVaultName --query properties.vaultUri --output tsv
    
    # Create the container app
    az containerapp create `
        --name $ContainerAppName `
        --resource-group $ResourceGroupName `
        --environment $ContainerEnvironmentName `
        --image $fullImageName `
        --user-assigned $identityId `
        --registry-server $acrLoginServer `
        --registry-identity $identityId `
        --target-port 8000 `
        --ingress external `
        --min-replicas 1 `
        --max-replicas 3 `
        --cpu 1.0 `
        --memory 2.0Gi `
        --env-vars "AZURE_CLIENT_ID=$clientId" "AZURE_STORAGE_ACCOUNT_NAME=$StorageAccountName" "AZURE_STORAGE_CONTAINER_NAME=models" "YOLO_MODEL_PATH=/app/models/yolov11x_best.pt" "KEY_VAULT_URI=$keyVaultUri" `
        --output table
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Container App" }
    
    Write-ColorOutput "✓ Container App '$ContainerAppName' created"
} catch {
    Write-ErrorOutput "✗ Failed to create Container App: $_"
    exit 1
}

Write-ColorOutput "`n=== Step 10: Getting Application URL ===" "Cyan"
try {
    Start-Sleep -Seconds 10  # Wait for app to be ready
    $appUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroupName --query properties.configuration.ingress.fqdn --output tsv
    if ($LASTEXITCODE -ne 0) { throw "Failed to get app URL" }
    
    $httpsUrl = "https://$appUrl"
    Write-ColorOutput "✓ Application deployed successfully!"
    Write-ColorOutput "🌐 Application URL: $httpsUrl" "Green"
    Write-ColorOutput "📚 API Documentation: $httpsUrl/docs" "Green"
    Write-ColorOutput "💚 Health Check: $httpsUrl/health" "Green"
} catch {
    Write-ErrorOutput "✗ Failed to get application URL: $_"
    exit 1
}

Write-ColorOutput "`n=== Deployment Summary ===" "Cyan"
Write-ColorOutput "Resource Group: $ResourceGroupName" "White"
Write-ColorOutput "Container Registry: $RegistryName.azurecr.io" "White"
Write-ColorOutput "Storage Account: $StorageAccountName" "White"
Write-ColorOutput "Key Vault: $KeyVaultName" "White"
Write-ColorOutput "Container App: $ContainerAppName" "White"
Write-ColorOutput "Application URL: $httpsUrl" "Green"

Write-ColorOutput "`n=== Testing the Deployment ===" "Cyan"
try {
    Write-ColorOutput "Testing health endpoint..."
    $response = Invoke-RestMethod -Uri "$httpsUrl/health" -Method Get -TimeoutSec 30
    if ($response.status -eq "healthy") {
        Write-ColorOutput "✓ Health check passed!" "Green"
    } else {
        Write-WarningOutput "⚠ Health check returned: $($response | ConvertTo-Json)"
    }
} catch {
    Write-WarningOutput "⚠ Could not test health endpoint (app may still be starting): $_"
}

Write-ColorOutput "`n🎉 Deployment completed successfully!" "Green"
Write-ColorOutput "Your translation API is now running at: $httpsUrl" "Green"
Write-ColorOutput "You can now test the PDF translation functionality!" "Green"

# Save deployment info to file
$deploymentInfo = @{
    ResourceGroup = $ResourceGroupName
    ContainerRegistry = "$RegistryName.azurecr.io"
    StorageAccount = $StorageAccountName
    KeyVault = $KeyVaultName
    ContainerApp = $ContainerAppName
    ApplicationUrl = $httpsUrl
    ApiDocs = "$httpsUrl/docs"
    HealthCheck = "$httpsUrl/health"
    DeploymentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
}

$deploymentInfo | ConvertTo-Json -Depth 2 | Out-File -FilePath "deployment-info.json" -Encoding UTF8
Write-ColorOutput "✓ Deployment information saved to deployment-info.json"
