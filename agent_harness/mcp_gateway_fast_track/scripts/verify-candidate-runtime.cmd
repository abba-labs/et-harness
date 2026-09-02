@echo off
setlocal
if "%~1"=="" (
  echo Usage: verify-candidate-runtime.cmd ^<release-manifest-path^> 1>&2
  exit /b 2
)
set "NODE_EXE=%ET_HARNESS_NODE%"
if not defined NODE_EXE if defined ET_HARNESS_ENV_ROOT set "NODE_EXE=%ET_HARNESS_ENV_ROOT%\runtimes\node-v22.23.2-win-x64\node.exe"
if not defined NODE_EXE set "NODE_EXE=%~dp0..\..\..\..\..\runtimes\node-v22.23.2-win-x64\node.exe"
if not exist "%NODE_EXE%" (
  echo ET Harness Node 22 runtime not found. Set ET_HARNESS_ENV_ROOT once or ET_HARNESS_NODE explicitly. 1>&2
  exit /b 1
)
"%NODE_EXE%" "%~dp0verify-candidate-runtime.mjs" "%~1"
exit /b %ERRORLEVEL%
