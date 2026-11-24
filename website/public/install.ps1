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
$serverUrl = "https://velo-compiler.github.io/velo"
if ($env:VELO_INSTALL_URL) {
    $serverUrl = $env:VELO_INSTALL_URL.TrimEnd('/')
}
if ($serverUrl -eq "https://velo-compiler.github.io") {
    $serverUrl = "https://velo-compiler.github.io/velo"
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
$downloadSuccess = $false
try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($downloadExeUrl, $targetExe)
    if ((Test-Path $targetExe) -and ((Get-Item $targetExe).Length -gt 0)) {
        $downloadSuccess = $true
    }
} catch {
    $downloadSuccess = $false
}

if (-not $downloadSuccess) {
    # Fallback A: GitHub Releases latest binary
    $githubReleaseExe = "https://github.com/velo-compiler/velo/releases/latest/download/velo.exe"
    try {
        Write-Host "--> Trying GitHub release binary from $githubReleaseExe..." -ForegroundColor Yellow
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($githubReleaseExe, $targetExe)
        if ((Test-Path $targetExe) -and ((Get-Item $targetExe).Length -gt 0)) {
            $downloadSuccess = $true
        }
    } catch {}
}

if (-not $downloadSuccess) {
    # Fallback B: Compile from bootstrap.c if GCC or Clang is installed locally
    $gccCmd = Get-Command gcc -ErrorAction SilentlyContinue
    $clangCmd = Get-Command clang -ErrorAction SilentlyContinue
    if ($gccCmd -or $clangCmd) {
        $cCompiler = if ($gccCmd) { "gcc" } else { "clang" }
        Write-Host "--> Compiling standalone compiler from bootstrap.c using $cCompiler..." -ForegroundColor Yellow
        $bootstrapUrls = @(
            "$serverUrl/bootstrap.c",
            "https://raw.githubusercontent.com/velo-compiler/velo/main/bootstrap.c"
        )
        $bootstrapFile = Join-Path $veloHome "bootstrap.c"
        $downloadedBootstrap = $false
        foreach ($bUrl in $bootstrapUrls) {
            try {
                $wc = New-Object System.Net.WebClient
                $wc.DownloadFile($bUrl, $bootstrapFile)
                if ((Test-Path $bootstrapFile) -and ((Get-Item $bootstrapFile).Length -gt 1000)) {
                    $downloadedBootstrap = $true
                    break
                }
            } catch {}
        }
        if ($downloadedBootstrap) {
            try {
                & $cCompiler -std=c99 -O2 $bootstrapFile -o $targetExe
                if ((Test-Path $targetExe) -and ((Get-Item $targetExe).Length -gt 0)) {
                    $downloadSuccess = $true
                    Write-Host "--> Successfully compiled standalone binary: $targetExe" -ForegroundColor Green
                }
            } catch {}
        }
    }
}

if (-not $downloadSuccess) {
    # Fallback C: Local repo binary candidates if cloned locally
    $localCandidates = @(
        (Join-Path $PSScriptRoot "..\..\bin\velo.exe"),
        (Join-Path $PSScriptRoot "velo.exe"),
        ".\bin\velo.exe",
        "..\bin\velo.exe",
        "..\..\bin\velo.exe",
        (Join-Path (Get-Location) "bin\velo.exe")
    )
    $found = $false
    foreach ($cand in $localCandidates) {
        if ($cand -and (Test-Path $cand)) {
            Write-Host "--> Falling back to local repo binary: $cand" -ForegroundColor Yellow
            Copy-Item -Force $cand $targetExe
            $found = $true
            $downloadSuccess = $true
            break
        }
    }
    if (-not $found) {
        Write-Error "Failed to install velo.exe from $($downloadExeUrl) and no local compiler or binary found."
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
    # Fallback A: GitHub releases or raw repo archive
    $fallbackStdUrls = @(
        "https://github.com/velo-compiler/velo/releases/latest/download/velo-std.zip",
        "https://github.com/velo-compiler/velo/archive/refs/heads/main.zip"
    )
    foreach ($fUrl in $fallbackStdUrls) {
        try {
            $wc = New-Object System.Net.WebClient
            $wc.DownloadFile($fUrl, $tempZip)
            if (Test-Path $tempZip) {
                Expand-Archive -Path $tempZip -DestinationPath $veloHome -Force
                Remove-Item -Force $tempZip -ErrorAction SilentlyContinue
                $installedStd = $true
                break
            }
        } catch {}
    }

    # Fallback B: Local repo directories
    $localStdCandidates = @(
        (Join-Path $PSScriptRoot "..\..\std"),
        ".\std",
        "..\std",
        "..\..\std",
        (Join-Path (Get-Location) "std")
    )
    foreach ($cand in $localStdCandidates) {
        if ($cand -and (Test-Path $cand)) {
            Write-Host "--> Copying standard library from local repo: $cand" -ForegroundColor Yellow
            Copy-Item -Recurse -Force (Join-Path $cand "*") $targetStd
            $installedStd = $true
            break
        }
    }
    $localRuntimeCandidates = @(
        (Join-Path $PSScriptRoot "..\..\runtime"),
        ".\runtime",
        "..\runtime",
        "..\..\runtime",
        (Join-Path (Get-Location) "runtime")
    )
    foreach ($cand in $localRuntimeCandidates) {
        if ($cand -and (Test-Path $cand)) {
            Copy-Item -Recurse -Force (Join-Path $cand "*") $targetRuntime
            break
        }
    }
}

# Ensure include/velo_runtime.h and runtime/velo_runtime.h exist
$runtimeHeader = Join-Path $targetRuntime "velo_runtime.h"
$includeHeader = Join-Path $targetInclude "velo_runtime.h"
if (Test-Path $runtimeHeader) {
    Copy-Item -Force $runtimeHeader $includeHeader
} elseif (Test-Path $includeHeader) {
    Copy-Item -Force $includeHeader $runtimeHeader
} else {
    $fallbackHeader = @(
        ".\runtime\velo_runtime.h",
        "..\runtime\velo_runtime.h",
        "..\..\runtime\velo_runtime.h",
        (Join-Path (Get-Location) "runtime\velo_runtime.h")
    )
    foreach ($fh in $fallbackHeader) {
        if ($fh -and (Test-Path $fh)) {
            Copy-Item -Force $fh $runtimeHeader
            Copy-Item -Force $fh $includeHeader
            break
        }
    }
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
