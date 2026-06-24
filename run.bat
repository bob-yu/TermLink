@echo off
setlocal
chcp 65001 >nul 2>&1

set "APP_NAME=TermLink"
set "DIST_EXE=%~dp0dist\%APP_NAME%\%APP_NAME%.exe"

if exist "%DIST_EXE%" (
    echo Running packaged executable: %DIST_EXE%
    start "" "%DIST_EXE%"
    exit /b 0
)

echo [ERROR] Built executable was not found:
echo         %DIST_EXE%
echo [HINT] Run build.bat first.
echo [HINT] For source development, run dev.bat.
exit /b 1
