@echo off
setlocal
set "NODE_EXE=%ET_HARNESS_NODE%"
if not defined NODE_EXE set "NODE_EXE=%~dp0..\..\..\..\..\runtimes\node-v22.23.2-win-x64\node.exe"
if not exist "%NODE_EXE%" (
  echo ET Harness Node 22 runtime not found: "%NODE_EXE%" 1>&2
  exit /b 1
)
"%NODE_EXE%" "%~dp0process-control.mjs" stop
exit /b %ERRORLEVEL%
