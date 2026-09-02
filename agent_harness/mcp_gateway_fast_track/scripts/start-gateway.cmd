@echo off
setlocal
set "NODE_EXE=%ET_HARNESS_NODE%"
if not defined NODE_EXE if defined ET_HARNESS_ENV_ROOT set "NODE_EXE=%ET_HARNESS_ENV_ROOT%\runtimes\node-v22.23.2-win-x64\node.exe"
if not defined NODE_EXE set "NODE_EXE=%~dp0..\..\..\..\..\runtimes\node-v22.23.2-win-x64\node.exe"
if not exist "%NODE_EXE%" (
  echo ET Harness Node 22 runtime not found. Set ET_HARNESS_ENV_ROOT once or ET_HARNESS_NODE explicitly. 1>&2
  exit /b 1
)
"%NODE_EXE%" "%~dp0freeze-runtime.mjs" --verify-only
if errorlevel 1 (
  echo Active Runtime release is missing or damaged. Build and activate a verified candidate, or rollback. 1>&2
  exit /b 1
)
"%NODE_EXE%" "%~dp0process-control.mjs" start
exit /b %ERRORLEVEL%
