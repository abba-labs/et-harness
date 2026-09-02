@echo off
setlocal
call "%~dp0prepare-toolchain.cmd"
exit /b %ERRORLEVEL%
