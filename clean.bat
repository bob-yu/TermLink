@echo off
setlocal
chcp 65001 >nul 2>&1

rem -----------------------------------------------------------------------------
rem Clean script for TermLink
rem Usage:
rem   clean.bat        -> clean build/release artifacts (safe default)
rem   clean.bat all    -> also remove runtime logs
rem   clean.bat help   -> show help
rem -----------------------------------------------------------------------------

set "MODE=%~1"
if /I "%MODE%"=="help" goto :help
if /I "%MODE%"=="-h" goto :help
if /I "%MODE%"=="--help" goto :help

set "CLEAN_LOGS=0"
if /I "%MODE%"=="all" set "CLEAN_LOGS=1"

cd /d "%~dp0"

echo ========================================
echo   TermLink Clean Script
echo ========================================
echo.

call :remove_dir "build"
call :remove_dir "dist"
call :remove_dir "portable"
call :remove_dir "release"
call :remove_dir "installer_output"

if "%CLEAN_LOGS%"=="1" (
    call :remove_dir "logs"
) else (
    echo [SKIP] logs ^(use "clean.bat all" to remove logs^)
)

echo [INFO] Removing Python cache files...
for /d /r %%D in (__pycache__) do (
    if exist "%%D" rd /s /q "%%D" >nul 2>&1
)
for /r %%F in (*.pyc *.pyo) do (
    if exist "%%F" del /f /q "%%F" >nul 2>&1
)

echo.
echo [DONE] Clean complete.
exit /b 0

:remove_dir
set "TARGET=%~1"
if exist "%TARGET%" (
    rd /s /q "%TARGET%" >nul 2>&1
    if exist "%TARGET%" (
        echo [WARN] Failed to remove %TARGET%
    ) else (
        echo [OK] Removed %TARGET%
    )
) else (
    echo [SKIP] %TARGET% ^(not found^)
)
exit /b 0

:help
echo Usage:
echo   clean.bat
echo     Clean build/release artifacts: build, dist, portable, release, installer_output
echo.
echo   clean.bat all
echo     Same as above, plus remove logs folder
echo.
echo   clean.bat help
echo     Show this help
exit /b 0

