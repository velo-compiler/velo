@echo off
setlocal
set PATH=C:\msys64\ucrt64\bin;%PATH%

if not exist "%~dp0..\..\bin\velo_survivors.exe" (
    echo [Velo] Building Velo Survivors with native compiler...
    cd /d "%~dp0"
    ..\..\bin\velo.exe build main.vl -o ..\..\bin\velo_survivors.exe -l raylib -l opengl32 -l gdi32 -l winmm
)

echo [Velo] Launching Velo Survivors...
cd /d "%~dp0..\.."
bin\velo_survivors.exe
