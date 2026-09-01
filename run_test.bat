@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD goto :no_python

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 goto :old_python

%PYTHON_CMD% tools\runner\bootstrap.py
set "ET_EXIT_CODE=%errorlevel%"

echo.
if "%ET_EXIT_CODE%"=="0" (
  echo Test run completed.
) else (
  echo Test run exited with code %ET_EXIT_CODE%.
)
echo.
pause
exit /b %ET_EXIT_CODE%

:no_python
echo [ERROR] Python was not found.
echo Install Python 3.10 or newer, then run this file again.
echo.
pause
exit /b 2

:old_python
echo [ERROR] Python 3.10 or newer is required.
echo Upgrade Python, then run this file again.
echo.
pause
exit /b 2
