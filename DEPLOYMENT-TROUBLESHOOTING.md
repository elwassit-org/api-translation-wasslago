# Azure Deployment Troubleshooting Guide

## Current Issue: Network Connectivity During Docker Build

You're experiencing DNS resolution and network timeouts when building the Docker image locally. This is common in corporate environments or when there are network restrictions.

## Solution Strategies (in order of recommendation)

### 🥇 **Strategy 1: Use Azure Cloud Shell (RECOMMENDED)**

Azure Cloud Shell has excellent connectivity to Azure services and package repositories.

1. **Upload your code to Azure Cloud Shell:**
   ```bash
   # In Azure Cloud Shell, clone your repo or upload files
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. **Run the deployment script:**
   ```bash
   chmod +x deploy-azure-cloudshell.sh
   ./deploy-azure-cloudshell.sh
   ```

3. **Benefits:**
   - No local Docker required
   - Uses ACR Tasks for building (faster, more reliable)
   - Direct Azure connectivity
   - No network restrictions

### 🥈 **Strategy 2: Use ACR Tasks (Azure Container Registry Build)**

Build the image in Azure instead of locally:

```powershell
# Login to Azure
az login

# Create resource group and ACR (if not exists)
az group create --name wasslago-rg --location "East US"
az acr create --name wasslagoacr --resource-group wasslago-rg --sku Basic --admin-enabled true

# Build using ACR Tasks (this happens in Azure, not locally)
az acr build --registry wasslagoacr --image wasslago-api:latest --file Dockerfile.resilient .
```

### 🥉 **Strategy 3: Fix Local Network Issues**

If you must build locally, try these approaches:

#### Option A: Use the Build Script with Network Testing
```powershell
# Test different approaches
.\build-docker.ps1 -UseMinimal                    # Try minimal dependencies
.\build-docker.ps1 -UseProxy -ProxyUrl "http://your-proxy:port"  # If behind corporate proxy
```

#### Option B: Configure Docker for Better Connectivity
```powershell
# Configure Docker daemon with DNS
# Create/edit %USERPROFILE%\.docker\daemon.json:
{
  "dns": ["8.8.8.8", "1.1.1.1"],
  "registry-mirrors": ["https://mirror.gcr.io"],
  "max-concurrent-downloads": 3,
  "max-concurrent-uploads": 3
}

# Restart Docker Desktop after making changes
```

#### Option C: Use Different Base Image
Create a Dockerfile with a different base:
```dockerfile
FROM ubuntu:22.04
# or
FROM debian:bullseye-slim
```

### 🆘 **Strategy 4: Use Pre-built Images**

Use a pre-built Python image with system dependencies already installed:

```dockerfile
FROM python:3.12-slim
# Minimal setup, use only pip packages
# No apt-get installations
```

## Network Diagnostics

Run these commands to diagnose network issues:

```powershell
# Test DNS resolution
nslookup deb.debian.org
nslookup pypi.org

# Test connectivity
Test-NetConnection -ComputerName deb.debian.org -Port 80
Test-NetConnection -ComputerName pypi.org -Port 443

# Check Docker network
docker network ls
docker network inspect bridge

# Test Docker connectivity
docker run --rm alpine:latest ping -c 3 google.com
```

## Quick Start Commands

### For Azure Cloud Shell:
```bash
# Upload your code to Cloud Shell
# Then run:
chmod +x deploy-azure-cloudshell.sh
./deploy-azure-cloudshell.sh
```

### For Local Build (if network works):
```powershell
.\build-docker.ps1
```

### For ACR Tasks Only:
```powershell
az acr build --registry wasslagoacr --image wasslago-api:latest --file Dockerfile.resilient .
```

## Expected Timeline

- **Azure Cloud Shell**: 15-20 minutes (recommended)
- **ACR Tasks**: 10-15 minutes  
- **Local Build**: 20-30 minutes (if network allows)

## Next Steps After Successful Build

1. **Deploy to Container Apps:**
   ```bash
   az containerapp create \
     --name wasslago-api \
     --resource-group wasslago-rg \
     --environment wasslago-env \
     --image wasslagoacr.azurecr.io/wasslago-api:latest \
     --registry-server wasslagoacr.azurecr.io \
     --target-port 8000 \
     --ingress external
   ```

2. **Configure Environment Variables:**
   - Add Gemini API key via Azure Key Vault
   - Set YOLO model path
   - Configure storage paths

3. **Test the Deployment:**
   - Health check: `https://your-app.region.azurecontainerapps.io/health`
   - API docs: `https://your-app.region.azurecontainerapps.io/docs`

## Troubleshooting Common Issues

### Issue: "DNS resolution failed"
**Solution:** Use Azure Cloud Shell or configure Docker DNS

### Issue: "Connection timeout"
**Solution:** Check firewall/proxy settings, use ACR Tasks

### Issue: "Package installation failed"
**Solution:** Use minimal Dockerfile or pre-built images

### Issue: "Docker daemon not running"
**Solution:** Start Docker Desktop or use Azure Cloud Shell

Choose the strategy that best fits your current network environment. Azure Cloud Shell is highly recommended as it bypasses all local network issues.
