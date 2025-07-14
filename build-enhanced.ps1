# Enhanced Docker Build Script with Multiple Strategies
# Run this script if the direct build fails

param(
    [string]$ImageName = "wasslago-api",
    [string]$Tag = "latest",
    [switch]$UseMultiStage = $false,
    [switch]$UseProxy = $false,
    [string]$ProxyUrl = ""
)

Write-Host "=== Enhanced Docker Build with Network Resilience ===" -ForegroundColor Green

# Function to test network connectivity to various mirrors
function Test-Mirrors {
    $mirrors = @(
        "pypi.org",
        "pypi.python.org", 
        "pypi.mirrors.ustc.edu.cn",
        "mirrors.aliyun.com",
        "pypi.douban.com",
        "files.pythonhosted.org"
    )
    
    Write-Host "Testing PyPI mirrors connectivity..." -ForegroundColor Yellow
    foreach ($mirror in $mirrors) {
        try {
            $result = Test-NetConnection -ComputerName $mirror -Port 443 -WarningAction SilentlyContinue
            if ($result.TcpTestSucceeded) {
                Write-Host "✓ $mirror: Available" -ForegroundColor Green
            } else {
                Write-Host "✗ $mirror: Failed" -ForegroundColor Red
            }
        } catch {
            Write-Host "✗ $mirror: Error" -ForegroundColor Red
        }
    }
}

# Function to build with different strategies
function Build-WithStrategy {
    param($Strategy, $DockerFile, $BuildArgs = @())
    
    Write-Host "Attempting build with strategy: $Strategy" -ForegroundColor Cyan
    
    $allArgs = @(
        "build"
        "-f", $DockerFile
        "-t", "${ImageName}:${Tag}"
        "--progress=plain"
    ) + $BuildArgs + @(".")
    
    Write-Host "Command: docker $($allArgs -join ' ')" -ForegroundColor Gray
    
    $process = Start-Process -FilePath "docker" -ArgumentList $allArgs -NoNewWindow -Wait -PassThru
    return $process.ExitCode -eq 0
}

# Main execution
try {
    Test-Mirrors
    
    # Strategy 1: Network-resilient Dockerfile
    Write-Host "`n=== Strategy 1: Network-Resilient Build ===" -ForegroundColor Yellow
    if (Build-WithStrategy "Network-Resilient" "Dockerfile.network-resilient" @("--network=default")) {
        Write-Host "✓ Success with network-resilient build!" -ForegroundColor Green
        exit 0
    }
    
    # Strategy 2: Use buildkit with cache mount
    Write-Host "`n=== Strategy 2: BuildKit with Cache ===" -ForegroundColor Yellow
    $env:DOCKER_BUILDKIT = "1"
    if (Build-WithStrategy "BuildKit-Cache" "Dockerfile.network-resilient" @("--cache-from", "type=local,src=.docker-cache", "--cache-to", "type=local,dest=.docker-cache")) {
        Write-Host "✓ Success with BuildKit cache!" -ForegroundColor Green
        exit 0
    }
    
    # Strategy 3: Multi-stage minimal build
    Write-Host "`n=== Strategy 3: Creating Minimal Build ===" -ForegroundColor Yellow
    
    # Create a minimal Dockerfile for testing
    $minimalDockerfile = @"
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app

# Install only essential system packages
RUN apt-get update && apt-get install -y \
    poppler-utils \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install only core packages
RUN pip install --no-cache-dir --timeout 300 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    requests==2.32.3 \
    aiofiles==24.1.0 \
    python-dotenv==1.0.0 \
    azure-storage-blob==12.19.0 \
    azure-identity==1.15.0 \
    google-generativeai==0.3.2

COPY . .

RUN mkdir -p /app/temp /app/doc /app/translated /app/models

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"@
    
    $minimalDockerfile | Out-File -FilePath "Dockerfile.minimal" -Encoding UTF8
    
    if (Build-WithStrategy "Minimal" "Dockerfile.minimal") {
        Write-Host "✓ Success with minimal build!" -ForegroundColor Green
        Write-Host "Note: This build has reduced functionality (no YOLO, OCR, etc.)" -ForegroundColor Yellow
        exit 0
    }
    
    # Strategy 4: Use proxy if specified
    if ($UseProxy -and $ProxyUrl) {
        Write-Host "`n=== Strategy 4: Proxy Build ===" -ForegroundColor Yellow
        $proxyArgs = @(
            "--build-arg", "HTTP_PROXY=$ProxyUrl"
            "--build-arg", "HTTPS_PROXY=$ProxyUrl"
            "--build-arg", "NO_PROXY=localhost,127.0.0.1"
        )
        
        if (Build-WithStrategy "Proxy" "Dockerfile.network-resilient" $proxyArgs) {
            Write-Host "✓ Success with proxy build!" -ForegroundColor Green
            exit 0
        }
    }
    
    # All strategies failed
    Write-Host "`n❌ All build strategies failed!" -ForegroundColor Red
    Write-Host "Alternative solutions:" -ForegroundColor Yellow
    Write-Host "1. Use Azure Cloud Shell: upload project and run 'az acr build'" -ForegroundColor White
    Write-Host "2. Use GitHub Actions or Azure DevOps for automated builds" -ForegroundColor White
    Write-Host "3. Try building during off-peak hours" -ForegroundColor White
    Write-Host "4. Check corporate firewall/proxy settings" -ForegroundColor White
    Write-Host "5. Use WSL2 with different network configuration" -ForegroundColor White
    
} catch {
    Write-Host "Script error: $($_.Exception.Message)" -ForegroundColor Red
}

# Cleanup
$env:DOCKER_BUILDKIT = $null
