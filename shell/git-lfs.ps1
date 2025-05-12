#####################################################################
## 已经克隆仓库的客户端使用的迁移脚本
#####################################################################


# Function: Check if command exists
function Test-CommandExists {
    param (
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )
    return (Get-Command $CommandName -ErrorAction SilentlyContinue) -ne $null
}

# Check if Chocolatey is installed
if (-not (Test-CommandExists -CommandName "choco.exe")) {
    Write-Output "Chocolatey not detected, installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

    # Wait for installation to complete
    Start-Sleep -Seconds 10

    # Check if Chocolatey installation was successful
    if (-not (Test-CommandExists -CommandName "choco.exe")) {
        Write-Error "Chocolatey installation failed! Please check network or other issues!"
        exit 1
    }
}
else {
    Write-Output "Chocolatey is already installed, continuing..."
}

# Check if git-lfs is installed
if (-not (Test-CommandExists -CommandName "git-lfs.exe")) {
    Write-Output "git-lfs not detected, installing via Chocolatey..."
    choco install git-lfs -y | Out-Null

    # Wait for git-lfs installation
    Start-Sleep -Seconds 5

    # Check if installation was successful
    if (-not (Test-CommandExists -CommandName "git-lfs.exe")) {
        Write-Error "git-lfs installation failed! Please check Chocolatey logs or install manually!"
        exit 1
    }
    else {
        Write-Output "git-lfs installed successfully."
    }
}
else {
    Write-Output "git-lfs is already installed."
}

Write-Output "All software installation completed."
# Script End

# Initialize git lfs in current directory
Write-Host "Initializing Git LFS..." -ForegroundColor Cyan
git lfs install

# Set error handling
$ErrorActionPreference = "Stop"

# Define branches to process
$BRANCHES = @("master", "test", "release")

# Process each branch
foreach ($branch in $BRANCHES) {
    Write-Host "`nProcessing $branch branch..." -ForegroundColor Yellow
    
    try {
        # Switch to specified branch
        Write-Host "Switching to $branch branch..." -ForegroundColor Cyan
        git checkout $branch
        
        # Force sync with remote branch
        Write-Host "Force syncing $branch branch with remote..." -ForegroundColor Cyan
        git fetch origin
        git reset --hard "origin/$branch"
        
        # Pull LFS files
        Write-Host "Pulling LFS files..." -ForegroundColor Cyan
        git lfs pull
        
        Write-Host "$branch branch sync completed" -ForegroundColor Green
    }
    catch {
        Write-Host "Error processing $branch branch: $_" -ForegroundColor Red
        continue
    }
}

Write-Host "`nAll branches sync completed" -ForegroundColor Green

# Perform repository cleanup
Write-Host "`nStarting repository cleanup..." -ForegroundColor Yellow
try {
    # Expire all reflog entries
    Write-Host "Expiring reflog entries..." -ForegroundColor Cyan
    git reflog expire --expire=now --all
    
    # Run garbage collection with aggressive pruning
    Write-Host "Running garbage collection..." -ForegroundColor Cyan
    git gc --prune=now --aggressive
    
    Write-Host "Repository cleanup completed successfully" -ForegroundColor Green
}
catch {
    Write-Host "Error during cleanup: $_" -ForegroundColor Red
    Write-Host "You may need to run cleanup manually" -ForegroundColor Yellow
}

Write-Host "`nScript execution completed" -ForegroundColor Green