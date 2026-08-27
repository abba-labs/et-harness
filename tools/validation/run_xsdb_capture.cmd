@echo off
setlocal
call "%~1" "%~2" > "%~3" 2>&1
set "xsdb_exit=%errorlevel%"
type "%~3"
exit /b %xsdb_exit%
