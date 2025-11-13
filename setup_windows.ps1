# AI Audio Summarizer - Windows Setup Script
# Run this script as Administrator

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "AI Audio Summarizer - Windows Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if running as Administrator
function Test-Administrator {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Host "Warning: This script should be run as Administrator for best results." -ForegroundColor Yellow
    Write-Host "Some features may not install correctly without admin privileges." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') {
        exit
    }
}

# Check if Python is installed
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Make sure to check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
    exit 1
}

# Check Python version
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
$majorVersion = [int]$matches[1]
$minorVersion = [int]$matches[2]

if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
    Write-Host "✗ Python 3.8 or higher is required. Found: $pythonVersion" -ForegroundColor Red
    exit 1
}

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip | Out-Null
Write-Host "✓ pip upgraded" -ForegroundColor Green

# Install Python dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Gray

$packages = @("sounddevice", "scipy", "numpy", "openai-whisper", "requests")

foreach ($package in $packages) {
    Write-Host "  Installing $package..." -ForegroundColor Gray
    python -m pip install $package --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ $package installed" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to install $package" -ForegroundColor Red
    }
}

# Check if Ollama is installed
Write-Host ""
Write-Host "Checking for Ollama..." -ForegroundColor Yellow
$ollamaInstalled = $false

try {
    $ollamaVersion = ollama --version 2>&1
    $ollamaInstalled = $true
    Write-Host "✓ Ollama found" -ForegroundColor Green
} catch {
    Write-Host "! Ollama not found" -ForegroundColor Yellow
}

if (-not $ollamaInstalled) {
    Write-Host ""
    Write-Host "Ollama needs to be installed manually." -ForegroundColor Yellow
    Write-Host "Please download and install from: https://ollama.com/download" -ForegroundColor Cyan
    Write-Host ""
    $install = Read-Host "Have you installed Ollama? (y/n)"
    
    if ($install -ne 'y') {
        Write-Host ""
        Write-Host "Please install Ollama and run this script again." -ForegroundColor Yellow
        exit 1
    }
}

# Start Ollama (if not already running)
Write-Host ""
Write-Host "Checking Ollama service..." -ForegroundColor Yellow

$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    $ollamaRunning = $true
    Write-Host "✓ Ollama service is running" -ForegroundColor Green
} catch {
    Write-Host "! Ollama service is not running" -ForegroundColor Yellow
    Write-Host "Starting Ollama..." -ForegroundColor Yellow
    
    # Try to start Ollama in the background
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Host "✓ Ollama service started" -ForegroundColor Green
        $ollamaRunning = $true
    } catch {
        Write-Host "! Could not start Ollama automatically" -ForegroundColor Yellow
        Write-Host "Please run 'ollama serve' in a separate terminal" -ForegroundColor Yellow
    }
}

# Pull the default model
if ($ollamaRunning) {
    Write-Host ""
    Write-Host "Pulling granite3.3:2b model (this may take several minutes)..." -ForegroundColor Yellow
    ollama pull granite3.3:2b
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ granite3.3:2b model ready" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to pull model" -ForegroundColor Red
        Write-Host "You can do this manually later with: ollama pull granite3.3:2b" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Skipping model download (Ollama not running)" -ForegroundColor Yellow
    Write-Host "After starting Ollama, run: ollama pull granite3.3:2b" -ForegroundColor Cyan
}

# Create a batch file for easy launching
Write-Host ""
Write-Host "Creating launch shortcut..." -ForegroundColor Yellow

$batchContent = @"
@echo off
title AI Audio Summarizer
echo Starting AI Audio Summarizer...
echo.
python Windows_audio_summarizer.py
pause
"@

Set-Content -Path "run_summarizer.bat" -Value $batchContent
Write-Host "✓ Created run_summarizer.bat" -ForegroundColor Green

# Final message
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the audio summarizer:" -ForegroundColor White
Write-Host "  Option 1: Double-click run_summarizer.bat" -ForegroundColor Cyan
Write-Host "  Option 2: python Windows_audio_summarizer.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Make sure Ollama is running:" -ForegroundColor White
Write-Host "  ollama serve" -ForegroundColor Cyan
Write-Host ""
Write-Host "Optional: Pull additional models:" -ForegroundColor White
Write-Host "  ollama pull llama3.2:1b" -ForegroundColor Gray
Write-Host "  ollama pull llama3.2:3b" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit"
