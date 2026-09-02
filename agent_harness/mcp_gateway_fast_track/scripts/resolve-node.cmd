@echo off
rem Shared bootstrap resolver for every ET Harness command entry.
rem Resolution order: explicit Node -> machine environment root -> legacy committed pointer.
set "NODE_EXE="
if defined ET_HARNESS_NODE set "NODE_EXE=%ET_HARNESS_NODE%"
if not defined NODE_EXE if defined ET_HARNESS_ENV_ROOT set "NODE_EXE=%ET_HARNESS_ENV_ROOT%\runtimes\node-v22.23.2-win-x64\node.exe"
if not defined NODE_EXE (
  for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -Command "$p = Get-Content -Raw -LiteralPath '%~dp0..\config\gateway.local.json' ^| ConvertFrom-Json; if ($p.runtimeReleasePointerPath) { Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $p.runtimeReleasePointerPath)) }"`) do set "ET_HARNESS_ENV_ROOT=%%I"
  if defined ET_HARNESS_ENV_ROOT set "NODE_EXE=%ET_HARNESS_ENV_ROOT%\runtimes\node-v22.23.2-win-x64\node.exe"
)
if not defined NODE_EXE (
  echo ET Harness machine environment is not configured. Set ET_HARNESS_ENV_ROOT once. 1>&2
  exit /b 1
)
if not exist "%NODE_EXE%" (
  echo ET Harness Node 22.23.2 runtime not found: "%NODE_EXE%" 1>&2
  exit /b 1
)
exit /b 0
