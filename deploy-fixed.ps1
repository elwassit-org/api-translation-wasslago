# Azure Container Apps Deployment Script for WasslaGo Translation API
param(
    [string]$ResourceGroup = "rg-wasslago-prod",
    [string]$Location = "East US",
    [string]$ContainerRegistryName = "acrwasslago",
    [string]$StorageAccountName = "wasslago",
    [string]$KeyVaultName = "kv-wasslago",
    [string]$ContainerAppName = "app-wasslago",
    [string]$ContainerEnvName = "env-wasslago"
)

# Color output functions
function Write-ColorOutput($Message, $Color = "White") {
    Write-Host $Message -ForegroundColor $Color
}

function Write-ErrorOutput($Message) {
    Write-Host $Message -ForegroundColor Red
}

function Write-SuccessOutput($Message) {
    Write-Host $Message -ForegroundColor Green
}

Write-ColorOutput "=== Azure Container Apps Deployment ===" "Cyan"
Write-ColorOutput "Starting deployment of WasslaGo Translation API..." "Yellow"

# Validate environment variables
if (-not $env:GEMINI_API_KEY) {
    Write-ErrorOutput "ERROR: GEMINI_API_KEY environment variable is not set"
    exit 1
}

Write-SuccessOutput "Environment variables validated"

# Create Resource Group
Write-ColorOutput "`nStep 1: Creating Resource Group..." "Yellow"
try {
    $rgExists = az group exists --name $ResourceGroup --output tsv
    if ($rgExists -eq "false") {
        az group create --name $ResourceGroup --location $Location
        Write-SuccessOutput "Resource group '$ResourceGroup' created"
    } else {
        Write-SuccessOutput "Resource group '$ResourceGroup' already exists"
    }
} catch {
    Write-ErrorOutput "Failed to create resource group: $_"
    exit 1
}

# Create Container Registry
Write-ColorOutput "`nStep 2: Creating Container Registry..." "Yellow"
try {
    $acrExists = az acr show --name $ContainerRegistryName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
    if (-not $acrExists) {
        az acr create --resource-group $ResourceGroup --name $ContainerRegistryName --sku Basic --admin-enabled true
        Write-SuccessOutput "Container Registry '$ContainerRegistryName' created"
    } else {
        Write-SuccessOutput "Container Registry '$ContainerRegistryName' already exists"
    }
} catch {
    Write-ErrorOutput "Failed to create container registry: $_"
    exit 1
}

# Get ACR login server
try {
    $acrLoginServer = az acr show --name $ContainerRegistryName --resource-group $ResourceGroup --query "loginServer" --output tsv
    Write-SuccessOutput "ACR Login Server: $acrLoginServer"
} catch {
    Write-ErrorOutput "Failed to get ACR login server: $_"
    exit 1
}

# Tag and push Docker image
Write-ColorOutput "`nStep 3: Pushing Docker image to ACR..." "Yellow"
try {
    $imageName = "wasslago-api"
    $imageTag = "latest"
    $fullImageName = "$acrLoginServer/${imageName}:${imageTag}"
    
    # Tag the image
    docker tag wasslago-api:fixed $fullImageName
    Write-SuccessOutput "Image tagged as: $fullImageName"
    
    # Login to ACR
    az acr login --name $ContainerRegistryName
    Write-SuccessOutput "Logged into ACR"
    
    # Push the image
    docker push $fullImageName
    Write-SuccessOutput "Image pushed to ACR successfully"
} catch {
    Write-ErrorOutput "Failed to push image to ACR: $_"
    exit 1
}

# Create Storage Account
Write-ColorOutput "`nStep 4: Creating Storage Account..." "Yellow"
try {
    $storageExists = az storage account show --name $StorageAccountName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
    if (-not $storageExists) {
        az storage account create --name $StorageAccountName --resource-group $ResourceGroup --location $Location --sku Standard_LRS --kind StorageV2
        Write-SuccessOutput "Storage Account '$StorageAccountName' created"
    } else {
        Write-SuccessOutput "Storage Account '$StorageAccountName' already exists"
    }
} catch {
    Write-ErrorOutput "Failed to create storage account: $_"
    exit 1
}

# Get storage account key
try {
    $storageKey = az storage account keys list --resource-group $ResourceGroup --account-name $StorageAccountName --query "[0].value" --output tsv
    Write-SuccessOutput "Storage account key retrieved"
} catch {
    Write-ErrorOutput "Failed to get storage account key: $_"
    exit 1
}

# Create blob container for YOLO model
Write-ColorOutput "`nStep 5: Creating blob container for YOLO model..." "Yellow"
try {
    az storage container create --name "models" --account-name $StorageAccountName --account-key $storageKey --public-access blob
    Write-SuccessOutput "Blob container 'models' created"
} catch {
    Write-ErrorOutput "Failed to create blob container: $_"
    exit 1
}

# Upload YOLO model
Write-ColorOutput "`nStep 6: Uploading YOLO model..." "Yellow"
try {
    if (Test-Path "models/yolov11x_best.pt") {
        az storage blob upload --account-name $StorageAccountName --account-key $storageKey --container-name "models" --name "yolov11x_best.pt" --file "models/yolov11x_best.pt"
        Write-SuccessOutput "YOLO model uploaded successfully"
    } else {
        Write-ErrorOutput "YOLO model file not found at models/yolov11x_best.pt"
        exit 1
    }
} catch {
    Write-ErrorOutput "Failed to upload YOLO model: $_"
    exit 1
}

# Create Key Vault
Write-ColorOutput "`nStep 7: Creating Key Vault..." "Yellow"
try {
    $kvExists = az keyvault show --name $KeyVaultName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
    if (-not $kvExists) {
        az keyvault create --name $KeyVaultName --resource-group $ResourceGroup --location $Location
        Write-SuccessOutput "Key Vault '$KeyVaultName' created"
    } else {
        Write-SuccessOutput "Key Vault '$KeyVaultName' already exists"
    }
} catch {
    Write-ErrorOutput "Failed to create Key Vault: $_"
    exit 1
}

# Store secrets in Key Vault
Write-ColorOutput "`nStep 8: Storing secrets in Key Vault..." "Yellow"
try {
    az keyvault secret set --vault-name $KeyVaultName --name "gemini-api-key" --value $env:GEMINI_API_KEY
    az keyvault secret set --vault-name $KeyVaultName --name "storage-account-key" --value $storageKey
    Write-SuccessOutput "Secrets stored in Key Vault"
} catch {
    Write-ErrorOutput "Failed to store secrets: $_"
    exit 1
}

# Create Container Apps Environment
Write-ColorOutput "`nStep 9: Creating Container Apps Environment..." "Yellow"
try {
    $envExists = az containerapp env show --name $ContainerEnvName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
    if (-not $envExists) {
        az containerapp env create --name $ContainerEnvName --resource-group $ResourceGroup --location $Location
        Write-SuccessOutput "Container Apps Environment '$ContainerEnvName' created"
    } else {
        Write-SuccessOutput "Container Apps Environment '$ContainerEnvName' already exists"
    }
} catch {
    Write-ErrorOutput "Failed to create Container Apps Environment: $_"
    exit 1
}

# Create Container App
Write-ColorOutput "`nStep 10: Creating Container App..." "Yellow"
try {
    $appExists = az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query "name" --output tsv 2>$null
    if (-not $appExists) {
        # Create the container app
        az containerapp create `
            --name $ContainerAppName `
            --resource-group $ResourceGroup `
            --environment $ContainerEnvName `
            --image $fullImageName `
            --target-port 8000 `
            --ingress external `
            --registry-server $acrLoginServer `
            --min-replicas 1 `
            --max-replicas 3 `
            --cpu 2.0 `
            --memory 4.0Gi `
            --env-vars GEMINI_API_KEY=secretref:gemini-api-key YOLO_MODEL_PATH=/app/models/yolov11x_best.pt STORAGE_ACCOUNT_NAME=$StorageAccountName STORAGE_CONTAINER_NAME=models AZURE_STORAGE_ACCOUNT_KEY=secretref:storage-account-key
        
        Write-SuccessOutput "Container App '$ContainerAppName' created"
    } else {
        Write-SuccessOutput "Container App '$ContainerAppName' already exists"
    }
} catch {
    Write-ErrorOutput "Failed to create Container App: $_"
    exit 1
}

# Set up Key Vault references
Write-ColorOutput "`nStep 11: Setting up Key Vault references..." "Yellow"
try {
    # Get the container app's managed identity
    $principalId = az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query "identity.principalId" --output tsv
    
    if ($principalId) {
        # Grant Key Vault access to the managed identity
        az keyvault set-policy --name $KeyVaultName --object-id $principalId --secret-permissions get list
        Write-SuccessOutput "Key Vault access granted to Container App"
    }
} catch {
    Write-ErrorOutput "Failed to set up Key Vault references: $_"
    exit 1
}

# Get application URL
Write-ColorOutput "`nStep 12: Getting application URL..." "Yellow"
try {
    $appUrl = az containerapp show --name $ContainerAppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" --output tsv
    $httpsUrl = "https://$appUrl"
    Write-SuccessOutput "Application deployed successfully!"
    Write-ColorOutput "Application URL: $httpsUrl" "Green"
    Write-ColorOutput "API Documentation: $httpsUrl/docs" "Green"
    Write-ColorOutput "Health Check: $httpsUrl/health" "Green"
} catch {
    Write-ErrorOutput "Failed to get application URL: $_"
    exit 1
}

Write-ColorOutput "`n=== Deployment Summary ===" "Cyan"
Write-ColorOutput "Resource Group: $ResourceGroup" "White"
Write-ColorOutput "Container Registry: $acrLoginServer" "White"
Write-ColorOutput "Storage Account: $StorageAccountName" "White"
Write-ColorOutput "Key Vault: $KeyVaultName" "White"
Write-ColorOutput "Container App: $ContainerAppName" "White"
Write-ColorOutput "Application URL: $httpsUrl" "Green"
Write-ColorOutput "`nDeployment completed successfully!" "Green"
