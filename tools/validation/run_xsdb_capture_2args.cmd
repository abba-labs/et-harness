@echo off
setlocal
if /I not "%~x2"==".tcl" (
    echo ERROR: second argument must be a Tcl script, got "%~2"
    exit /b 64
)
if /I "%~x3"==".tcl" (
    echo ERROR: refusing to use a Tcl script as the log output: "%~3"
    exit /b 64
)
if "%~5"=="" (
    call "%~1" "%~2" "%~4" > "%~3" 2>&1
) else (
    call "%~1" "%~2" "%~4" "%~5" > "%~3" 2>&1
)
set "xsdb_exit=%errorlevel%"
type "%~3"
findstr /C:"SELFTEST_PASS|0" "%~3" >nul 2>&1
if not errorlevel 1 set "xsdb_exit=1"
exit /b %xsdb_exit%
