@echo off
rem Shared bootstrap resolver for every ET Harness command entry.
rem Resolution order: explicit Node -> machine environment root -> legacy committed pointer.
set "NODE_EXE="
if defined ET_HARNESS_NODE goto verify_explicit_node
if defined ET_HARNESS_ENV_ROOT goto derive_node_from_environment

for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0resolve-environment-root.ps1" "%~dp0..\config\gateway.local.json"`) do set "ET_HARNESS_ENV_ROOT=%%I"
if not defined ET_HARNESS_ENV_ROOT goto missing_environment

:derive_node_from_environment
set "NODE_EXE=%ET_HARNESS_ENV_ROOT%\runtimes\node-v22.23.2-win-x64\node.exe"
goto verify_node

:verify_explicit_node
set "NODE_EXE=%ET_HARNESS_NODE%"

:verify_node
if exist "%NODE_EXE%" exit /b 0
echo ET Harness Node 22.23.2 runtime not found: "%NODE_EXE%" 1>&2
exit /b 1

:missing_environment
echo ET Harness machine environment is not configured. Set ET_HARNESS_ENV_ROOT once. 1>&2
exit /b 1
