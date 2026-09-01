@echo off
setlocal
call "%~dp0scripts\start-gateway.cmd"
set "GATEWAY_EXIT_CODE=%ERRORLEVEL%"
if not "%GATEWAY_EXIT_CODE%"=="0" pause
exit /b %GATEWAY_EXIT_CODE%
