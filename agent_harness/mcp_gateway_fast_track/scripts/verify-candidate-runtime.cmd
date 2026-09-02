@echo off
setlocal
if "%~1"=="" (
  echo Usage: verify-candidate-runtime.cmd ^<release-manifest-path^> 1>&2
  exit /b 2
)
call "%~dp0resolve-node.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
"%NODE_EXE%" "%~dp0verify-candidate-runtime.mjs" "%~1"
exit /b %ERRORLEVEL%
