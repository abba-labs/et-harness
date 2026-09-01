@echo off
setlocal

rem Keep this cmd.exe launcher ASCII-only and CRLF-terminated.
rem The first argument may override the default company repository path.
set "TARGET_REPOSITORY=D:\lihuan\vibe_code\code\SDK\git\Et_Automated_Testing_Platform_Code\et_automated_testing_platform"
if not "%~1"=="" set "TARGET_REPOSITORY=%~1"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0sync_to_company_repo.ps1" ^
  -Destination "%TARGET_REPOSITORY%"

set "SYNC_EXIT_CODE=%ERRORLEVEL%"
echo.

if "%SYNC_EXIT_CODE%"=="2" (
  echo Synchronization was canceled. No files were changed.
) else if not "%SYNC_EXIT_CODE%"=="0" (
  echo Synchronization failed. No commit or push was performed.
) else (
  echo Synchronization finished. Review the target repository changes before committing.
)

pause
exit /b %SYNC_EXIT_CODE%
