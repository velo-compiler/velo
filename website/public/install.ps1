# Velo Programming Language One-Liner Windows Installer
# Usage: irm http://localhost:5173/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "   _  __     __" -ForegroundColor Cyan
Write-Host "  | | / /__ / /__" -ForegroundColor Cyan
Write-Host "  | |/ / -_) / _ \" -ForegroundColor Cyan
Write-Host "  |___/\__/_/\___/" -ForegroundColor Cyan
Write-Host ""
Write-Host "  >> Velo Systems Language Installer (v2.0 Native)" -ForegroundColor Green
Write-Host "  Code at high velocity." -ForegroundColor Gray
Write-Host ""

# Determine Host Server URL
$serverUrl = "http://localhost:5173"
if ($env:VELO_INSTALL_URL) {
    $serverUrl = $env:VELO_INSTALL_URL
}

$targetDir = Join-Path $HOME ".velo\bin"
$targetExe = Join-Path $targetDir "velo.exe"
$downloadUrl = "$serverUrl/velo.exe"

# 1. Create target directory
Write-Host "--> Creating target directory: $targetDir" -ForegroundColor Yellow
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
}

# 2. Download pre-compiled binary
Write-Host "--> Downloading standalone binary from $downloadUrl..." -ForegroundColor Yellow
try {
    # Use WebClient for high speed and progress handling
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($downloadUrl, $targetExe)
} catch {
    # Fallback to local copy if running from repo root
    $localExe = Join-Path $PSScriptRoot "..\..\bin\velo.exe"
    if (Test-Path $localExe) {
        Write-Host "--> Falling back to local repo binary: $localExe" -ForegroundColor Yellow
        Copy-Item -Force $localExe $targetExe
    } else {
        Write-Error "Failed to download velo.exe from $($downloadUrl). Error: $_"
        exit 1
    }
}

# Verify binary was created
if (-not (Test-Path $targetExe)) {
    Write-Error "Installation failed: $targetExe not found."
    exit 1
}

Write-Host "--> Binary installed: $targetExe" -ForegroundColor Green

# 3. Update User PATH environment variable if not already present
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -split ';' -notcontains $targetDir) {
    Write-Host "--> Adding $targetDir to your User PATH..." -ForegroundColor Yellow
    $newUserPath = if ([string]::IsNullOrEmpty($userPath)) { $targetDir } else { "$userPath;$targetDir" }
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    Write-Host "--> Added to persistent User PATH!" -ForegroundColor Green
} else {
    Write-Host "--> $targetDir is already in your PATH." -ForegroundColor Gray
}

# Update current session PATH so command is available immediately
$env:Path = "$env:Path;$targetDir"

# 4. Verify installation
Write-Host ""
Write-Host "--> Verifying installation..." -ForegroundColor Cyan
& "$targetExe" version

Write-Host ""
Write-Host "[OK] SUCCESS! Velo v2.0 is installed and ready to use." -ForegroundColor Green
Write-Host ""
Write-Host "To write your first program:" -ForegroundColor White
Write-Host "  1. Create a file named 'main.vl'" -ForegroundColor Gray
Write-Host "  2. Run: velo run main.vl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Enjoy coding at high velocity!" -ForegroundColor Green
Write-Host ""
