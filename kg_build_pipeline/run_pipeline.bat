@echo off
rem KG Build Pipeline — uses conda env tomluck2 (torch/neo4j verified).
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

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" kg_build_pipeline\run_pipeline.py --config kg_build_pipeline\config.yaml --all %*
if errorlevel 1 (
  echo Pipeline failed.
  pause
  exit /b 1
)
echo Pipeline finished OK.
pause
