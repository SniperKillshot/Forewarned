#!/usr/bin/env pwsh
# Deploy script for Forewarned Home Assistant Addon

param(
    [string]$Target = "local",  # "local" or "git"
    [string]$HAHost = "",       # Your HA IP/hostname
    [string]$Message = "Update"
)

Write-Host "Forewarned Deployment Script" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

if ($Target -eq "local") {
    if (-not $HAHost) {
        Write-Host "Error: Please specify -HAHost parameter" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Deploying to local Home Assistant: $HAHost" -ForegroundColor Yellow
    
    # Using SCP to copy files
    scp -r * root@${HAHost}:/addons/forewarned/
    
    Write-Host "Files copied. Please restart the addon in Home Assistant UI." -ForegroundColor Green
    
} elseif ($Target -eq "git") {
    Write-Host "Deploying via Git..." -ForegroundColor Yellow
    
    # Git workflow
    git add .
    git commit -m "$Message"
    git push
    
    Write-Host "Pushed to Git. Update addon in Home Assistant if needed." -ForegroundColor Green
    
} else {
    Write-Host "Unknown target: $Target" -ForegroundColor Red
    Write-Host "Usage: .\deploy.ps1 -Target [local|git] [-HAHost IP] [-Message 'commit message']"
    exit 1
}
