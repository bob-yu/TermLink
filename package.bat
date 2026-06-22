@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "APP_NAME=TermLink"
set "VERSION=1.0.5"
set "DIST_DIR=dist\%APP_NAME%"
set "PORTABLE_ROOT=portable"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%I"
set "PORTABLE_DIR=%PORTABLE_ROOT%\%APP_NAME%_v%VERSION%_win64_%TS%"
set "ZIP_FILE=%PORTABLE_ROOT%\%APP_NAME%_v%VERSION%_win64_%TS%.zip"

echo ========================================
echo   %APP_NAME% v%VERSION% Package
echo ========================================
echo.

if not exist "%DIST_DIR%\%APP_NAME%.exe" (
    echo [ERROR] Built executable was not found: %DIST_DIR%\%APP_NAME%.exe
    echo [HINT] Run build.bat first.
    exit /b 1
)

echo [1/4] Stopping running process...
taskkill /f /im %APP_NAME%.exe >nul 2>&1
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "if (Get-Process -Name '%APP_NAME%' -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 (
    echo [ERROR] %APP_NAME% is still running. Close it and run package.bat again.
    exit /b 1
)

echo [2/4] Creating portable folder...
mkdir "%PORTABLE_ROOT%" >nul 2>&1
if exist "%PORTABLE_DIR%" rmdir /s /q "%PORTABLE_DIR%"
robocopy "%DIST_DIR%" "%PORTABLE_DIR%" /E /XD "%DIST_DIR%\logs" "%DIST_DIR%\_internal\logs" /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo [ERROR] Failed to copy package files.
    exit /b 1
)

if not exist "%PORTABLE_DIR%\logs" mkdir "%PORTABLE_DIR%\logs"

echo [3/4] Writing portable launcher...
(
echo @echo off
echo setlocal
echo set "EXE=%%~dp0%APP_NAME%.exe"
echo if not exist "%%EXE%%" ^(
echo     echo [ERROR] Missing %%EXE%%
echo     exit /b 1
echo ^)
echo start "" "%%EXE%%"
echo endlocal
) > "%PORTABLE_DIR%\run.bat"

echo [4/4] Creating zip package...
set "ZIP_CREATED=0"
for /l %%R in (1,1,5) do (
    if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%" >nul 2>&1
    powershell -NoProfile -Command "Start-Sleep -Seconds 1; Compress-Archive -Path '%PORTABLE_DIR%\*' -DestinationPath '%ZIP_FILE%' -CompressionLevel Optimal -Force"
    if exist "%ZIP_FILE%" (
        for %%F in ("%ZIP_FILE%") do if %%~zF GTR 1048576 set "ZIP_CREATED=1"
    )
    if "!ZIP_CREATED!"=="1" goto :zip_done
    echo [WARN] Zip attempt %%R failed, retrying...
)

:zip_done
if not "%ZIP_CREATED%"=="1" (
    echo [ERROR] Zip creation failed: %ZIP_FILE%
    exit /b 1
)

for %%F in ("%ZIP_FILE%") do set "ZIP_SIZE=%%~zF"
set /a ZIP_MB=%ZIP_SIZE%/1024/1024

echo.
echo ========================================
echo Package complete.
echo Portable folder: %PORTABLE_DIR%
echo Portable zip:    %ZIP_FILE%
echo Zip size:        %ZIP_MB% MB
echo ========================================
endlocal
exit /b 0
