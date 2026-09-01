@echo off
setlocal
call "%~dp0freeze-runtime.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0verify-environment.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0stop-gateway.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
call "%~dp0start-gateway.cmd"
exit /b %ERRORLEVEL%
