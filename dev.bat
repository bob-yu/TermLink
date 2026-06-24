@echo off
setlocal
chcp 65001 >nul 2>&1

pushd "%~dp0"

echo ========================================
echo   TermLink Development Run
echo ========================================
echo.
echo Running from Python source: python main.py
echo.

python main.py
set "EXIT_CODE=%ERRORLEVEL%"

popd
endlocal & exit /b %EXIT_CODE%
