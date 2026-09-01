import { spawnSync } from 'node:child_process'

const FORBIDDEN_PROCESS_NAMES = new Set(['chatgpt.exe', 'codex.exe'])
const FORBIDDEN_COMMAND_FRAGMENTS = [
  '\\.codex\\plugins\\',
  '\\hooks\\',
  '\\marketplace\\',
]

export const findForbiddenLauncher = (processes) =>
  processes.find((processInfo) => {
    const name = String(processInfo.name ?? '').toLowerCase()
    const commandLine = String(processInfo.commandLine ?? '').toLowerCase()
    return (
      FORBIDDEN_PROCESS_NAMES.has(name) ||
      FORBIDDEN_COMMAND_FRAGMENTS.some((fragment) => commandLine.includes(fragment))
    )
  })

export const readAncestorProcesses = (processId = process.pid) => {
  const command = `
$ErrorActionPreference = 'Stop'
$currentProcessId = ${processId}
$seen = @{}
$rows = @()
for ($index = 0; $index -lt 16 -and $currentProcessId -gt 0; $index++) {
  if ($seen.ContainsKey($currentProcessId)) { break }
  $seen[$currentProcessId] = $true
  $current = Get-CimInstance Win32_Process -Filter "ProcessId = $currentProcessId"
  if ($null -eq $current) { break }
  $rows += [pscustomobject]@{
    processId = [int]$current.ProcessId
    parentProcessId = [int]$current.ParentProcessId
    name = [string]$current.Name
    commandLine = [string]$current.CommandLine
  }
  $currentProcessId = [int]$current.ParentProcessId
}
ConvertTo-Json -InputObject @($rows) -Compress
`
  const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', command], {
    encoding: 'utf8',
    windowsHide: true,
  })
  if (result.status !== 0 || !result.stdout.trim()) {
    throw new Error('Unable to verify the Gateway launcher ancestry')
  }
  const parsed = JSON.parse(result.stdout)
  return Array.isArray(parsed) ? parsed : [parsed]
}

export const assertExternalGatewayLauncher = () => {
  const processes = readAncestorProcesses()
  const forbidden = findForbiddenLauncher(processes)
  if (forbidden) {
    throw new Error(
      `Gateway startup rejected: ${forbidden.name} is in the launcher ancestry; start it from Windows Explorer or an independent terminal outside Codex Desktop`,
    )
  }
  return processes
}
