#!/usr/bin/env pwsh
# Git Setup Script for Forewarned
# Run this AFTER installing Git for Windows

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Forewarned Git Setup Assistant" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if Git is installed
try {
    $gitVersion = git --version
    Write-Host "✓ Git is installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Git for Windows from:" -ForegroundColor Yellow
    Write-Host "https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Then restart VS Code and run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Get user information
Write-Host "Git Configuration" -ForegroundColor Yellow
Write-Host "-----------------" -ForegroundColor Yellow
$userName = Read-Host "Enter your name (for Git commits)"
$userEmail = Read-Host "Enter your email (for Git commits)"

# Configure Git
git config --global user.name "$userName"
git config --global user.email "$userEmail"

Write-Host "✓ Git configured" -ForegroundColor Green
Write-Host ""

# Initialize repository
Write-Host "Initializing Git Repository..." -ForegroundColor Yellow
git init

# Check if already initialized
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Repository initialized" -ForegroundColor Green
} else {
    Write-Host "! Repository may already be initialized" -ForegroundColor Yellow
}

Write-Host ""

# Add files
Write-Host "Adding files to repository..." -ForegroundColor Yellow
git add .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Files staged" -ForegroundColor Green
}

Write-Host ""

# Initial commit
Write-Host "Creating initial commit..." -ForegroundColor Yellow
git commit -m "Initial commit: Forewarned HA addon with weather and EOC monitoring"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Initial commit created" -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Create a new repository on GitHub:" -ForegroundColor Yellow
Write-Host "   https://github.com/new" -ForegroundColor White
Write-Host ""
Write-Host "2. Copy your repository URL (example):" -ForegroundColor Yellow
Write-Host "   https://github.com/YOUR-USERNAME/forewarned.git" -ForegroundColor White
Write-Host ""

$repoUrl = Read-Host "Enter your GitHub repository URL (or press Enter to skip)"

if ($repoUrl) {
    Write-Host ""
    Write-Host "Connecting to GitHub..." -ForegroundColor Yellow
    
    git remote add origin $repoUrl
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Remote repository added" -ForegroundColor Green
        
        # Rename to main if needed
        git branch -M main
        
        Write-Host ""
        Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
        git push -u origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Code pushed to GitHub!" -ForegroundColor Green
            Write-Host ""
            Write-Host "==================================" -ForegroundColor Cyan
            Write-Host "Success! Your repository is on GitHub" -ForegroundColor Green
            Write-Host "==================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "3. Add to Home Assistant:" -ForegroundColor Yellow
            Write-Host "   Settings → Add-ons → Add-on Store → ⋮ → Repositories" -ForegroundColor White
            Write-Host "   Add: $repoUrl" -ForegroundColor Cyan
            Write-Host ""
        } else {
            Write-Host "✗ Failed to push to GitHub" -ForegroundColor Red
            Write-Host "You may need to authenticate with GitHub" -ForegroundColor Yellow
            Write-Host "Try running: git push -u origin main" -ForegroundColor White
        }
    }
} else {
    Write-Host ""
    Write-Host "Skipped GitHub connection." -ForegroundColor Yellow
    Write-Host "To connect later, run:" -ForegroundColor White
    Write-Host "  git remote add origin YOUR-GITHUB-URL" -ForegroundColor Cyan
    Write-Host "  git branch -M main" -ForegroundColor Cyan
    Write-Host "  git push -u origin main" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Repository setup complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "See GITHUB_SETUP.md for full documentation" -ForegroundColor Yellow
