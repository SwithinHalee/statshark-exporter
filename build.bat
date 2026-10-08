@echo off
title Build StatShark Fast Exporter GUI
cd /d "%~dp0"

echo [1/3] Checking Python environment...
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    set "PYINSTALLER_CMD=.venv\Scripts\pyinstaller.exe"
) else (
    set "PYTHON_CMD=python"
    set "PYINSTALLER_CMD=pyinstaller"
)

echo [2/3] Building standalone executable with PyInstaller...
%PYINSTALLER_CMD% --onefile --noconsole --name "StatShark_Fast_Exporter_GUI" StatShark_Exporter_GUI.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b %ERRORLEVEL%
)

echo [3/3] Deploying executable...
move /y "dist\StatShark_Fast_Exporter_GUI.exe" "StatShark_Fast_Exporter_GUI.exe"
rmdir /s /q "build"
rmdir /s /q "dist"
del /f /q "StatShark_Fast_Exporter_GUI.spec"

echo [SUCCESS] Build completed! StatShark_Fast_Exporter_GUI.exe is ready.
pause
