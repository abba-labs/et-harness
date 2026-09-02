@echo off
setlocal
if "%~1"=="" (
  echo Usage: configure-machine-environment.cmd ^<absolute-et-harness-env-root^> 1>&2
  exit /b 2
)
for %%I in ("%~1") do set "ENV_ROOT=%%~fI"
if not exist "%ENV_ROOT%\runtimes\node-v22.23.2-win-x64\node.exe" (
  echo ET Harness Node 22.23.2 runtime not found under "%ENV_ROOT%". 1>&2
  exit /b 1
)
setx ET_HARNESS_ENV_ROOT "%ENV_ROOT%" >nul
if errorlevel 1 exit /b %ERRORLEVEL%
echo ET_HARNESS_ENV_ROOT configured for future shells: "%ENV_ROOT%"
echo Current shell is unchanged; reopen the terminal before relying on the persisted setting.
exit /b 0
