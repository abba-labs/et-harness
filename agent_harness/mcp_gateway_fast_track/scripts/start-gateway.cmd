@echo off
setlocal
call "%~dp0resolve-node.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
"%NODE_EXE%" "%~dp0freeze-runtime.mjs" --verify-only
if errorlevel 1 (
  echo Active Runtime release is missing or damaged. Build and activate a verified candidate, or rollback. 1>&2
  exit /b 1
)
"%NODE_EXE%" "%~dp0process-control.mjs" start
exit /b %ERRORLEVEL%
