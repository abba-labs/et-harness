@echo off
setlocal
set "NODE_EXE=%ET_HARNESS_NODE%"
if not defined NODE_EXE set "NODE_EXE=%~dp0..\..\..\..\..\runtimes\node-v22.23.2-win-x64\node.exe"
if not exist "%NODE_EXE%" (
  echo ET Harness Node 22 runtime not found: "%NODE_EXE%" 1>&2
  exit /b 1
)
call "%~dp0freeze-runtime.cmd" --verify-only
if errorlevel 1 exit /b %ERRORLEVEL%
"%NODE_EXE%" "%~dp0..\node_modules\typescript\bin\tsc" -p "%~dp0..\tsconfig.runtime-bundle.json"
if errorlevel 1 exit /b %ERRORLEVEL%
pushd "%~dp0.."
"%NODE_EXE%" --test tests\*.test.mjs
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
