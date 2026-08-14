@echo off
REM ============================================
REM  CaoNiGe Toolbox - dependency installer
REM ============================================
setlocal

REM find a usable python launcher
set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3.11"
where %PY% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

echo Installing dependencies: PySide6 / Pillow / pywin32 / pytest / pytest-qt
echo PySide6 is large, please wait a few minutes...
echo.

%PY% -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo.
    echo [FAILED] Install failed. Check network, then retry with mirror:
    echo   %PY% -m pip install -r requirements-dev.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)

echo.
echo [OK] Dependencies installed.
echo   Run app:    %PY% -m cng_toolbox.main
echo   Run tests:  %PY% -m pytest
echo   Build exe:  set CNG_ONEFILE=1 ^& pyinstaller build.spec
echo.
pause
