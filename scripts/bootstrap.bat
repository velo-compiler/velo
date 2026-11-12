@echo off
setlocal

echo [Velo] Bootstrapping Velo Native Compiler from bootstrap.c...

if not exist "bin" mkdir "bin"

rem 1. Check known MSYS2 GCC locations first (ensuring clean DLL resolution)
if exist "C:\msys64\ucrt64\bin\gcc.exe" (
    echo [Velo] Found GCC at C:\msys64\ucrt64\bin\gcc.exe...
    set "PATH=C:\msys64\ucrt64\bin;%PATH%"
    gcc -O2 -std=c99 -I runtime -I velo/runtime bootstrap.c -o bin\velo.exe
    if %ERRORLEVEL% equ 0 goto success
)

if exist "C:\msys64\mingw64\bin\gcc.exe" (
    echo [Velo] Found GCC at C:\msys64\mingw64\bin\gcc.exe...
    set "PATH=C:\msys64\mingw64\bin;%PATH%"
    gcc -O2 -std=c99 -I runtime -I velo/runtime bootstrap.c -o bin\velo.exe
    if %ERRORLEVEL% equ 0 goto success
)

rem 2. Check GCC in existing PATH
where gcc >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [Velo] Using GCC from PATH...
    gcc -O2 -std=c99 -I runtime -I velo/runtime bootstrap.c -o bin\velo.exe
    if %ERRORLEVEL% equ 0 goto success
)

rem 3. Check Clang in PATH
where clang >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [Velo] Using Clang from PATH...
    clang -O2 -std=c99 -I runtime -I velo/runtime bootstrap.c -o bin\velo.exe
    if %ERRORLEVEL% equ 0 goto success
)

rem 4. Check MSVC cl in PATH
where cl >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [Velo] Using MSVC cl from PATH...
    cl /nologo /O2 /TC /wd4090 /wd4996 /D_CRT_SECURE_NO_WARNINGS /I runtime /I velo/runtime bootstrap.c /Fe:bin\velo.exe
    if %ERRORLEVEL% equ 0 goto success
)

rem 5. Probe Visual Studio installations for vcvars64.bat
set "VCVARS="
if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
)

if defined VCVARS (
    echo [Velo] Found MSVC at "%VCVARS%". Initializing and compiling bootstrap.c...
    call "%VCVARS%" >nul
    cl /nologo /O2 /TC /wd4090 /wd4996 /D_CRT_SECURE_NO_WARNINGS /I runtime /I velo/runtime bootstrap.c /Fe:bin\velo.exe
    if %ERRORLEVEL% equ 0 goto success
)

echo [Velo Error] No supported C compiler found (GCC, Clang, or MSVC cl).
echo Please install GCC (MSYS2 UCRT64) or Visual Studio, or ensure your compiler is in PATH.
exit /b 1

:success
echo [Velo] Successfully bootstrapped bin\velo.exe from bootstrap.c.
bin\velo.exe version

if "%1"=="--full" goto full_bootstrap
if "%1"=="/full" goto full_bootstrap
if "%1"=="-f" goto full_bootstrap
exit /b 0

:full_bootstrap
echo.
echo [Velo] Commencing 3-stage self-hosting verification (Gen1 -^> Gen2 -^> Gen3)...
echo [Velo] Building Gen2 compiler (bin\velo.exe build src/main.vl -o bin\velo_gen2.exe)...
bin\velo.exe build src/main.vl -o bin\velo_gen2.exe
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

echo [Velo] Building Gen3 compiler (bin\velo_gen2.exe build src/main.vl -o bin\velo_gen3.exe)...
bin\velo_gen2.exe build src/main.vl -o bin\velo_gen3.exe
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

echo [Velo] Verifying SHA-256 fixed-point determinism...
python scripts\check_determinism.py
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

copy /Y bin\velo_gen3.exe bin\velo.exe >nul
echo [Velo] Bootstrap complete! Canonical bin\velo.exe is verified deterministic Gen3.
exit /b 0
