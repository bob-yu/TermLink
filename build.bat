@echo off
setlocal
chcp 65001 >nul 2>&1

set "APP_NAME=TermLink"
set "DIST_DIR=dist\%APP_NAME%"

echo ========================================
echo   %APP_NAME% Build
echo ========================================
echo.

echo [1/3] Stopping running process...
taskkill /f /im %APP_NAME%.exe >nul 2>&1
powershell -NoProfile -Command "Start-Sleep -Seconds 1"
powershell -NoProfile -Command "if (Get-Process -Name '%APP_NAME%' -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 (
    echo [ERROR] %APP_NAME% is still running. Close it and run build.bat again.
    exit /b 1
)

echo [2/3] Cleaning build output...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [3/3] Building executable package...
python -m PyInstaller --noconfirm TermLink.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

if not exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo [ERROR] Missing executable after build: %DIST_DIR%\%APP_NAME%.exe
    exit /b 1
)

echo.
echo ========================================
echo Build complete.
echo Executable: %DIST_DIR%\%APP_NAME%.exe
echo Run command: run.bat
echo ========================================
endlocal
exit /b 0
