# Uninstalls all versions of the Velo VS Code extension
Write-Host "Uninstalling Velo VS Code extension..." -ForegroundColor Cyan

# prefer the official CLI uninstall when available
$code = Get-Command code -ErrorAction SilentlyContinue
if ($code) {
    & code --uninstall-extension velo.velo-lang 2>$null | Out-Null
}

# folder-module installs and leftovers are cleaned regardless
$dirs = Get-ChildItem "$env:USERPROFILE\.vscode\extensions" -Directory -Filter "velo.velo-lang-*" -ErrorAction SilentlyContinue
if (-not $dirs) {
    Write-Host "Velo extension folder install not found (all clean)." -ForegroundColor Yellow
} else {
    $dirs | Remove-Item -Recurse -Force
    Write-Host "Removed: $($dirs.Name -join ', ')" -ForegroundColor Green
}
Write-Host "Run 'Developer: Reload Window' in VS Code to finish." -ForegroundColor Green
