@echo off
rem KG Build Pipeline Web UI — uses conda env tomluck2.
rem Override: set PIPELINE_PYTHON=C:\path\to\python.exe before running.
cd /d "%~dp0.."

set "PYTHON_EXE=C:\Users\tom\.conda\envs\tomluck2\python.exe"
if defined PIPELINE_PYTHON set "PYTHON_EXE=%PIPELINE_PYTHON%"

if not exist "%PYTHON_EXE%" (
  echo ERROR: Python not found: %PYTHON_EXE%
  echo Set PIPELINE_PYTHON to a working interpreter, or install conda env tomluck2.
  pause
  exit /b 1
)

rem If UI already listening on 8765, just open browser (do not start a second server).
netstat -ano | findstr "LISTENING" | findstr ":8765" >nul
if not errorlevel 1 (
  echo UI already running on http://127.0.0.1:8765
  echo Opening browser. Do not close the existing UI PowerShell/cmd window.
  start "" "http://127.0.0.1:8765"
  pause
  exit /b 0
)

echo Using Python: %PYTHON_EXE%
echo Starting KG Build UI at http://127.0.0.1:8765
echo Keep this window open while using the UI.
"%PYTHON_EXE%" -m kg_build_pipeline.ui.app
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
  echo.
  echo UI server exited with code %EXITCODE%.
  echo If you saw "address already in use" / WinError 10048, another UI is already on port 8765.
  echo Fix: close the other UI window, or open http://127.0.0.1:8765 directly.
  pause
  exit /b %EXITCODE%
)
