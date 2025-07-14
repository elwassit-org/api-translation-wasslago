# Local Docker Build Script with Network Workarounds
# Run this from PowerShell in your project directory

param(
    [string]$ImageName = "wasslago-api",
    [string]$Tag = "latest",
    [string]$ACRName = "wasslagoacr",
    [switch]$UseMinimal = $false,
    [switch]$UseProxy = $false,
    [string]$ProxyUrl = ""
)

Write-Host "=== Docker Build Script with Network Resilience ===" -ForegroundColor Green

# Function to test network connectivity
function Test-NetworkConnectivity {
    Write-Host "Testing network connectivity..." -ForegroundColor Yellow
    
    $tests = @(
        @{Name="Google DNS"; Host="8.8.8.8"; Port=53},
        @{Name="Docker Hub"; Host="registry-1.docker.io"; Port=443},
        @{Name="Python PyPI"; Host="pypi.org"; Port=443},
        @{Name="Debian Archive"; Host="deb.debian.org"; Port=80}
    )
    
    foreach ($test in $tests) {
        try {
            $result = Test-NetConnection -ComputerName $test.Host -Port $test.Port -WarningAction SilentlyContinue
            if ($result.TcpTestSucceeded) {
                Write-Host "✓ $($test.Name): Connected" -ForegroundColor Green
            } else {
                Write-Host "✗ $($test.Name): Failed" -ForegroundColor Red
            }
        } catch {
            Write-Host "✗ $($test.Name): Error - $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

# Function to configure Docker for proxy
function Set-DockerProxy {
    param($ProxyUrl)
    
    if ($ProxyUrl) {
        Write-Host "Configuring Docker to use proxy: $ProxyUrl" -ForegroundColor Yellow
        $env:HTTP_PROXY = $ProxyUrl
        $env:HTTPS_PROXY = $ProxyUrl
        $env:NO_PROXY = "localhost,127.0.0.1,.local"
    }
}

# Function to build Docker image with retries
function Build-DockerImageWithRetry {
    param(
        [string]$Dockerfile,
        [string]$ImageName,
        [string]$Tag,
        [int]$MaxRetries = 3
    )
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        Write-Host "Build attempt $i of $MaxRetries..." -ForegroundColor Yellow
        
        $buildArgs = @(
            "build"
            "-f", $Dockerfile
            "-t", "${ImageName}:${Tag}"
            "--network=default"
            "--progress=plain"
            "."
        )
        
        # Add build args for better caching and network handling
        if ($UseProxy -and $ProxyUrl) {
            $buildArgs += "--build-arg", "HTTP_PROXY=$ProxyUrl"
            $buildArgs += "--build-arg", "HTTPS_PROXY=$ProxyUrl"
            $buildArgs += "--build-arg", "NO_PROXY=localhost,127.0.0.1,.local"
        }
        
        Write-Host "Running: docker $($buildArgs -join ' ')" -ForegroundColor Cyan
        
        $process = Start-Process -FilePath "docker" -ArgumentList $buildArgs -NoNewWindow -Wait -PassThru
        
        if ($process.ExitCode -eq 0) {
            Write-Host "✓ Build successful!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ Build attempt $i failed with exit code $($process.ExitCode)" -ForegroundColor Red
            if ($i -lt $MaxRetries) {
                Write-Host "Waiting 30 seconds before retry..." -ForegroundColor Yellow
                Start-Sleep -Seconds 30
            }
        }
    }
    
    Write-Host "✗ All build attempts failed!" -ForegroundColor Red
    return $false
}

# Main execution
try {
    # Test network connectivity
    Test-NetworkConnectivity
    
    # Configure proxy if specified
    if ($UseProxy) {
        Set-DockerProxy -ProxyUrl $ProxyUrl
    }
    
    # Choose Dockerfile
    $dockerfile = if ($UseMinimal) { "Dockerfile.minimal" } else { "Dockerfile.resilient" }
    
    if (-not (Test-Path $dockerfile)) {
        Write-Host "✗ Dockerfile not found: $dockerfile" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Using Dockerfile: $dockerfile" -ForegroundColor Cyan
    
    # Attempt to build
    $buildSuccess = Build-DockerImageWithRetry -Dockerfile $dockerfile -ImageName $ImageName -Tag $Tag
    
    if ($buildSuccess) {
        Write-Host "=== Build completed successfully! ===" -ForegroundColor Green
        
        # Show image info
        Write-Host "Image built: ${ImageName}:${Tag}" -ForegroundColor Cyan
        docker images $ImageName
        
        # Test the image locally
        Write-Host "Testing image locally..." -ForegroundColor Yellow
        $testProcess = Start-Process -FilePath "docker" -ArgumentList @("run", "--rm", "-d", "-p", "8000:8000", "${ImageName}:${Tag}") -NoNewWindow -Wait -PassThru -RedirectStandardOutput "container_id.txt"
        
        if ($testProcess.ExitCode -eq 0) {
            $containerId = Get-Content "container_id.txt"
            Write-Host "✓ Container started with ID: $containerId" -ForegroundColor Green
            Write-Host "Test the API at: http://localhost:8000/health" -ForegroundColor Cyan
            Write-Host "Stop the container with: docker stop $containerId" -ForegroundColor Yellow
            Remove-Item "container_id.txt" -ErrorAction SilentlyContinue
        }
        
        # Offer to push to ACR
        if ($ACRName) {
            $push = Read-Host "Push to Azure Container Registry '$ACRName'? (y/N)"
            if ($push -eq "y" -or $push -eq "Y") {
                Write-Host "Pushing to ACR..." -ForegroundColor Yellow
                
                # Login to ACR
                az acr login --name $ACRName
                
                # Tag for ACR
                $acrImage = "${ACRName}.azurecr.io/${ImageName}:${Tag}"
                docker tag "${ImageName}:${Tag}" $acrImage
                
                # Push to ACR
                docker push $acrImage
                
                Write-Host "✓ Image pushed to ACR: $acrImage" -ForegroundColor Green
            }
        }
        
    } else {
        Write-Host "=== Build failed! ===" -ForegroundColor Red
        Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
        Write-Host "1. Check your internet connection" -ForegroundColor White
        Write-Host "2. Try using Azure Cloud Shell: deploy-azure-cloudshell.ps1" -ForegroundColor White
        Write-Host "3. Try the minimal build: -UseMinimal" -ForegroundColor White
        Write-Host "4. Configure corporate proxy: -UseProxy -ProxyUrl 'http://proxy:port'" -ForegroundColor White
        Write-Host "5. Use ACR Tasks: az acr build --registry $ACRName --image ${ImageName}:latest ." -ForegroundColor White
    }
    
} catch {
    Write-Host "✗ Script error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
