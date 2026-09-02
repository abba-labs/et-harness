@echo off
setlocal
call "%~dp0resolve-node.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
"%NODE_EXE%" "%~dp0install-machine-launcher.mjs"
exit /b %ERRORLEVEL%
