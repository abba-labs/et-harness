@echo off
setlocal
set "NODE_EXE=%ET_HARNESS_NODE%"
if not defined NODE_EXE set "NODE_EXE=%~dp0..\..\..\..\..\runtimes\node-v22.23.2-win-x64\node.exe"
set "NPM_CLI=%~dp0..\..\..\..\..\runtimes\node-v22.23.2-win-x64\node_modules\npm\bin\npm-cli.js"
set "ET_TEMP=%~dp0..\..\..\..\..\temp\pure-mcp-npm"
set "ET_CACHE=%~dp0..\..\..\..\..\cache\npm"
if not exist "%NODE_EXE%" (
  echo ET Harness Node 22 runtime not found: "%NODE_EXE%" 1>&2
  exit /b 1
)
if not exist "%NPM_CLI%" (
  echo ET Harness npm runtime not found: "%NPM_CLI%" 1>&2
  exit /b 1
)
if not exist "%ET_TEMP%" mkdir "%ET_TEMP%"
if not exist "%ET_CACHE%" mkdir "%ET_CACHE%"
set "TEMP=%ET_TEMP%"
set "TMP=%ET_TEMP%"
set "npm_config_cache=%ET_CACHE%"
pushd "%~dp0.."
"%NODE_EXE%" "%NPM_CLI%" ci --ignore-scripts --no-audit --no-fund
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
