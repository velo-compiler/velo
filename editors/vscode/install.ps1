# Installs the Velo VS Code extension. Version is read from package.json.
$root = $PSScriptRoot
$pkg = Get-Content (Join-Path $root "package.json") -Raw | ConvertFrom-Json
$version = $pkg.version
$dest = "$env:USERPROFILE\.vscode\extensions\velo.velo-lang-$version"

Write-Host "Installing Velo VS Code extension v$version..." -ForegroundColor Cyan

# start clean: remove any folder-copy installs of this extension so the two
# install paths never leave duplicates
Get-ChildItem "$env:USERPROFILE\.vscode\extensions" -Directory -Filter "velo.velo-lang-*" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Path A: use the official VS Code CLI when available
$vsix = Join-Path $root "velo-lang-$version.vsix"
$code = Get-Command code -ErrorAction SilentlyContinue
if ($code -and (-not (Test-Path $vsix)) -and (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Building package velo-lang-$version.vsix..." -ForegroundColor Cyan
    & python (Join-Path $root "pack_vsix.py")
}
if ($code -and (Test-Path $vsix)) {
    & code --install-extension $vsix --force
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installed via 'code --install-extension'. Run 'Developer: Reload Window' to activate." -ForegroundColor Green
        return
    }
    Write-Host "VS Code CLI install failed; falling back to folder copy." -ForegroundColor Yellow
}

# Path B: copy this source tree into a versioned extensions folder
Write-Host "Copying to $dest" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "*") $dest
# remove superseded versions of this extension so .obsolete state never accumulates
Get-ChildItem "$env:USERPROFILE\.vscode\extensions" -Directory -Filter "velo.velo-lang-*" |
    Where-Object { $_.FullName -ne $dest } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Done! Run 'Developer: Reload Window' in VS Code to activate." -ForegroundColor Green
