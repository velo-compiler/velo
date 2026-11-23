@echo off
REM Velo pre-commit hook (Windows): enforces canonical formatting via `velo fmt --check`.
python "%~dp0..\check_formatting.py" --staged
exit /b %errorlevel%
