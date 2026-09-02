@echo off
setlocal
for %%I in ("%~dp0..") do set "ET_MACHINE_ROOT=%%~fI"
set "ET_MACHINE_NODE=%ET_MACHINE_ROOT%\runtimes\node-v22.23.2-win-x64\node.exe"
if not exist "%ET_MACHINE_NODE%" (
  echo Fixed ET Harness Node runtime is unavailable: "%ET_MACHINE_NODE%" 1>&2
  exit /b 1
)
"%ET_MACHINE_NODE%" "%~dp0machine-launcher.mjs" %*
exit /b %ERRORLEVEL%
