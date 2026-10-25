@echo off
setlocal
set PATH=C:\msys64\ucrt64\bin;%PATH%

if not exist "%~dp0..\..\bin\velo_craft.exe" (
    echo [Velo] Building VeloCraft (3D Voxel Sandbox) with native compiler...
    cd /d "%~dp0"
    ..\..\bin\velo.exe build main.vl -o ..\..\bin\velo_craft.exe -l raylib -l opengl32 -l gdi32 -l winmm
)

echo [Velo] Launching VeloCraft...
cd /d "%~dp0..\.."
bin\velo_craft.exe
