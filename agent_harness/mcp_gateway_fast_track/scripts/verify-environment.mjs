import { spawnSync } from 'node:child_process'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { resolve } from 'node:path'

import {
  ET_HARNESS_ENV_ROOT_VAR,
  EXPECTED_NODE_VERSION,
  layout,
  packageRoot,
} from './environment-layout.mjs'
import { resolveCurrentToolchain } from './toolchain.mjs'

if (process.version !== EXPECTED_NODE_VERSION) {
  throw new Error(`ET Harness verification requires ${EXPECTED_NODE_VERSION}; current Node is ${process.version}`)
}

const toolchain = resolveCurrentToolchain()
const typecheckRoot = resolve(layout.tempRoot, 'shared-toolchain-typecheck')
mkdirSync(typecheckRoot, { recursive: true })
const generatedConfig = resolve(typecheckRoot, `tsconfig.${process.pid}.json`)

const sourceConfig = JSON.parse(readFileSync(resolve(packageRoot, 'tsconfig.runtime-bundle.json'), 'utf8'))
const paths = {}
for (const [name, values] of Object.entries(sourceConfig.compilerOptions?.paths ?? {})) {
  if (name === '@deepseek-ai/cordis' || name === 'yaml') continue
  paths[name] = values.map(value => resolve(packageRoot, value))
}

const cordisTypes = resolve(
  toolchain.toolchainRoot,
  'node_modules',
  '@deepseek-ai',
  'cordis',
  'lib',
  'types',
  'index.d.ts',
)
const yamlTypes = resolve(
  toolchain.toolchainRoot,
  'node_modules',
  'yaml',
  'dist',
  'index.d.ts',
)
for (const [name, path] of [
  ['@deepseek-ai/cordis', cordisTypes],
  ['yaml', yamlTypes],
]) {
  if (!existsSync(path)) throw new Error(`Shared Toolchain TypeScript entry is unavailable for ${name}: ${path}`)
}
paths['@deepseek-ai/cordis'] = [cordisTypes]
paths.yaml = [yamlTypes]

const config = {
  ...sourceConfig,
  compilerOptions: {
    ...(sourceConfig.compilerOptions ?? {}),
    baseUrl: packageRoot,
    typeRoots: [resolve(toolchain.toolchainRoot, 'node_modules', '@types')],
    paths,
  },
  include: (sourceConfig.include ?? []).map(value => resolve(packageRoot, value)),
}
writeFileSync(generatedConfig, `${JSON.stringify(config, null, 2)}\n`, 'utf8')

const run = (label, args, options = {}) => {
  const result = spawnSync(process.execPath, args, {
    cwd: options.cwd ?? packageRoot,
    encoding: 'utf8',
    windowsHide: true,
    env: {
      ...process.env,
      [ET_HARNESS_ENV_ROOT_VAR]: layout.environmentRoot,
      ...(options.env ?? {}),
    },
  })
  if (result.status !== 0) {
    const detail = [result.stderr, result.stdout].filter(value => value?.trim()).join('\n').trim()
    throw new Error(`${label} failed with exit ${result.status}${detail ? `: ${detail}` : ''}`)
  }
  return result.stdout.trim()
}

try {
  const tscPath = resolve(toolchain.toolchainRoot, 'node_modules', 'typescript', 'bin', 'tsc')
  run('Runtime TypeScript verification', [tscPath, '-p', generatedConfig])

  const testFiles = readdirSync(resolve(packageRoot, 'tests'))
    .filter(name => name.endsWith('.test.mjs') && name !== 'frozen-runtime-wiring.test.mjs')
    .sort()
    .map(name => resolve(packageRoot, 'tests', name))
  if (testFiles.length === 0) throw new Error('Gateway verification found no source .test.mjs files')
  run(
    'Gateway source regression tests',
    ['--import', resolve(packageRoot, 'scripts', 'register-toolchain-loader.mjs'), '--test', ...testFiles],
  )

  process.stdout.write(`${JSON.stringify({
    status: 'SOURCE_ENVIRONMENT_VERIFIED',
    nodeVersion: process.version,
    toolchainId: toolchain.descriptor.toolchainId,
    dependencyCount: Object.keys(toolchain.dependencyVersions).length,
    sourceGatewayTestCount: testFiles.length,
    activeRuntimeBehaviorUsedAsCandidateEvidence: false,
    checkoutNodeModulesRequired: false,
  })}\n`)
} finally {
  rmSync(generatedConfig, { force: true })
}
