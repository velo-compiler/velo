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

$veloHome = Join-Path $HOME ".velo"
$targetDir = Join-Path $veloHome "bin"
$targetExe = Join-Path $targetDir "velo.exe"
$targetStd = Join-Path $veloHome "std"
$targetInclude = Join-Path $veloHome "include"
$targetRuntime = Join-Path $veloHome "runtime"

$downloadExeUrl = "$serverUrl/velo.exe"
$downloadStdUrl = "$serverUrl/velo-std.zip"

# 1. Create target directories
Write-Host "--> Creating target directories in $veloHome..." -ForegroundColor Yellow
@($targetDir, $targetStd, $targetInclude, $targetRuntime) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Force -Path $_ | Out-Null
    }
}

# 2. Download and install pre-compiled binary
Write-Host "--> Downloading standalone compiler from $downloadExeUrl..." -ForegroundColor Yellow
try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($downloadExeUrl, $targetExe)
} catch {
    # Fallback to local copy if running from repo root
    $localExe = Join-Path $PSScriptRoot "..\..\bin\velo.exe"
    if (Test-Path $localExe) {
        Write-Host "--> Falling back to local repo binary: $localExe" -ForegroundColor Yellow
        Copy-Item -Force $localExe $targetExe
    } else {
        Write-Error "Failed to download velo.exe from $($downloadExeUrl). Error: $_"
        exit 1
    }
}

if (-not (Test-Path $targetExe)) {
    Write-Error "Installation failed: $targetExe not found."
    exit 1
}
Write-Host "--> Binary installed: $targetExe" -ForegroundColor Green

# 3. Download and install Standard Library & C Runtime Header
Write-Host "--> Installing Standard Library & Runtime headers..." -ForegroundColor Yellow
$tempZip = Join-Path ([System.IO.Path]::GetTempPath()) "velo-std.zip"
$installedStd = $false

try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($downloadStdUrl, $tempZip)
    if (Test-Path $tempZip) {
        Expand-Archive -Path $tempZip -DestinationPath $veloHome -Force
        Remove-Item -Force $tempZip -ErrorAction SilentlyContinue
        $installedStd = $true
    }
} catch {
    # Fallback to local repo directories
    $localStd = Join-Path $PSScriptRoot "..\..\std"
    $localRuntime = Join-Path $PSScriptRoot "..\..\runtime"
    if (Test-Path $localStd) {
        Write-Host "--> Copying standard library from local repo: $localStd" -ForegroundColor Yellow
        Copy-Item -Recurse -Force (Join-Path $localStd "*") $targetStd
        if (Test-Path $localRuntime) {
            Copy-Item -Recurse -Force (Join-Path $localRuntime "*") $targetRuntime
        }
        $installedStd = $true
    }
}

# Ensure include/velo_runtime.h exists
$runtimeHeader = Join-Path $targetRuntime "velo_runtime.h"
if (Test-Path $runtimeHeader) {
    Copy-Item -Force $runtimeHeader (Join-Path $targetInclude "velo_runtime.h")
}

Write-Host "--> Standard library installed: $targetStd" -ForegroundColor Green

# 4. Configure persistent environment variables
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -split ';' -notcontains $targetDir) {
    Write-Host "--> Adding $targetDir to your User PATH..." -ForegroundColor Yellow
    $newUserPath = if ([string]::IsNullOrEmpty($userPath)) { $targetDir } else { "$userPath;$targetDir" }
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    Write-Host "--> Added to persistent User PATH!" -ForegroundColor Green
} else {
    Write-Host "--> $targetDir is already in your PATH." -ForegroundColor Gray
}

# Set VELO_HOME and VELO_STD
[Environment]::SetEnvironmentVariable("VELO_HOME", $veloHome, "User")
[Environment]::SetEnvironmentVariable("VELO_STD", $targetStd, "User")

# Update current session environment so command is ready immediately
$env:Path = "$env:Path;$targetDir"
$env:VELO_HOME = $veloHome
$env:VELO_STD = $targetStd

# 5. Verify installation
Write-Host ""
Write-Host "--> Verifying installation..." -ForegroundColor Cyan
& "$targetExe" version

Write-Host ""
Write-Host "[OK] SUCCESS! Velo v2.0 is installed and ready to use." -ForegroundColor Green
Write-Host ""
Write-Host "To write your first program:" -ForegroundColor White
Write-Host "  1. Create a file named 'main.vl' with:" -ForegroundColor Gray
Write-Host "       use std.io" -ForegroundColor Cyan
Write-Host "       act main() {" -ForegroundColor Cyan
Write-Host "           io.println_str(""Hello, Velo!"")" -ForegroundColor Cyan
Write-Host "       }" -ForegroundColor Cyan
Write-Host "  2. Run: velo run main.vl" -ForegroundColor White
Write-Host ""
Write-Host "Enjoy coding at high velocity!" -ForegroundColor Green
Write-Host ""
