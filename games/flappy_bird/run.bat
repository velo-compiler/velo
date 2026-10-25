@echo off
set PATH=C:\msys64\ucrt64\bin;%PATH%
echo Launching Flappy Bird in Velo...
..\..\bin\velo.exe run game.vl -l raylib -l opengl32 -l gdi32 -l winmm
