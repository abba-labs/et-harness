import { createHash } from 'node:crypto'
import { readdirSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = dirname(fileURLToPath(import.meta.url))
export const packageRoot = resolve(scriptDirectory, '..')
export const repositoryRoot = resolve(packageRoot, '..', '..')
export const environmentRoot = resolve(repositoryRoot, '..', '..')
const requireFromPackage = createRequire(resolve(packageRoot, 'package.json'))

const packageEntries = Object.freeze({
  '@agent-harness/governance-core': 'agent_harness/governance_core/src/index.ts',
  '@agent-harness/project-contract': 'agent_harness/project_contract/src/index.ts',
  '@agent-harness/project-manager': 'agent_harness/public_plugins/project_manager/src/index.ts',
  '@agent-harness/architecture-navigator': 'agent_harness/public_plugins/architecture_navigator/src/index.ts',
  '@agent-harness/rule-manager': 'agent_harness/public_plugins/rule_manager/src/index.ts',
  '@agent-harness/evidence-state-manager': 'agent_harness/public_plugins/evidence_state_manager/src/index.ts',
  '@agent-harness/knowledge-manager': 'agent_harness/public_plugins/knowledge_manager/src/index.ts',
  '@agent-harness/gate-manager': 'agent_harness/public_plugins/gate_manager/src/index.ts',
  '@agent-harness/context-builder': 'agent_harness/public_plugins/context_builder/src/index.ts',
  '@agent-harness/experience-memory-manager': 'agent_harness/public_plugins/experience_memory_manager/src/index.ts',
  '@agent-harness/agent-governance-kernel': 'agent_harness/public_plugins/agent_governance_kernel/src/index.ts',
  '@agent-harness/agent-governance-closure-adapters': 'agent_harness/public_plugins/agent_governance_closure_adapters/src/index.ts',
  '@agent-harness/auto-governance-engine': 'agent_harness/public_plugins/auto_governance_engine/src/index.ts',
  '@agent-harness/governance-runtime': 'agent_harness/public_plugins/governance_runtime/src/index.ts',
  '@agent-harness/execution-supervisor': 'agent_harness/public_plugins/execution_supervisor/src/index.ts',
})

export const localPackageAliases = Object.freeze(
  {
    ...Object.fromEntries(
      Object.entries(packageEntries).map(([name, path]) => [name, resolve(repositoryRoot, path)]),
    ),
    '@deepseek-ai/cordis': requireFromPackage.resolve('@deepseek-ai/cordis'),
    yaml: requireFromPackage.resolve('yaml'),
  },
)

export const runtimeOwnerEntry = resolve(packageRoot, 'src', 'runtime-owner.ts')
export const runtimeBootstrapEntry = resolve(packageRoot, 'src', 'project-bootstrap.ts')
export const atpProjectPluginEntry = resolve(
  repositoryRoot,
  'agent_harness',
  'projects',
  'automated_testing_platform',
  'src',
  'index.ts',
)

const walkFiles = (directory) => {
  const files = []
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) files.push(...walkFiles(path))
    else if (entry.isFile() && entry.name.endsWith('.ts')) files.push(path)
  }
  return files
}

export const runtimeSourceFiles = () => {
  const packageDirectories = new Set(
    Object.values(packageEntries).map((entry) => resolve(repositoryRoot, entry, '..', '..')),
  )
  packageDirectories.add(resolve(atpProjectPluginEntry, '..', '..'))
  const files = [
    runtimeOwnerEntry,
    runtimeBootstrapEntry,
    resolve(packageRoot, 'package.json'),
    resolve(packageRoot, 'package-lock.json'),
    resolve(packageRoot, 'scripts', 'freeze-runtime.mjs'),
    fileURLToPath(import.meta.url),
  ]
  for (const directory of packageDirectories) {
    files.push(resolve(directory, 'package.json'))
    files.push(...walkFiles(resolve(directory, 'src')))
  }
  return [...new Set(files)].sort((left, right) => left.localeCompare(right))
}

export const computeRuntimeSourceSignature = () => {
  const digest = createHash('sha256')
  digest.update(`repositoryRoot\0${repositoryRoot.toLowerCase()}\0`)
  for (const path of runtimeSourceFiles()) {
    digest.update(relative(repositoryRoot, path).replaceAll('\\', '/'))
    digest.update('\0')
    digest.update(readFileSync(path))
    digest.update('\0')
  }
  return digest.digest('hex')
}

export const resolveEnvironmentPath = (...parts) => resolve(environmentRoot, ...parts)
