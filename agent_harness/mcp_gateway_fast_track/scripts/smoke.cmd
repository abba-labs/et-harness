@echo off
setlocal
call "%~dp0resolve-node.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
pushd "%~dp0.."
if errorlevel 1 exit /b %ERRORLEVEL%
"%NODE_EXE%" --import "./scripts/register-toolchain-loader.mjs" "./scripts/smoke.mjs"
set "SMOKE_EXIT=%ERRORLEVEL%"
popd
exit /b %SMOKE_EXIT%
