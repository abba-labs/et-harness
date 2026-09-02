@echo off
setlocal
call "%~dp0resolve-node.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
"%NODE_EXE%" --import "%~dp0register-toolchain-loader.mjs" "%~dp0smoke.mjs"
exit /b %ERRORLEVEL%
