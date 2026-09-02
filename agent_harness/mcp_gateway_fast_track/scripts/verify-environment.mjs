import { spawnSync } from 'node:child_process'
import {
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
import {
  resolveCurrentToolchain,
} from './toolchain.mjs'

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

const packageTypeEntry = name => {
  const packageManifestPath = resolve(toolchain.toolchainRoot, 'node_modules', ...name.split('/'), 'package.json')
  const manifest = JSON.parse(readFileSync(packageManifestPath, 'utf8'))
  const entry = manifest.types ?? manifest.typings
  if (typeof entry !== 'string' || !entry.trim()) {
    throw new Error(`Shared Toolchain package does not declare TypeScript types: ${name}`)
  }
  return resolve(packageManifestPath, '..', entry)
}
paths['@deepseek-ai/cordis'] = [packageTypeEntry('@deepseek-ai/cordis')]
paths.yaml = [packageTypeEntry('yaml')]

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
    .filter(name => name.endsWith('.test.mjs'))
    .sort()
    .map(name => resolve(packageRoot, 'tests', name))
  if (testFiles.length === 0) throw new Error('Gateway verification found no .test.mjs files')
  run(
    'Gateway source regression tests',
    ['--import', resolve(packageRoot, 'scripts', 'register-toolchain-loader.mjs'), '--test', ...testFiles],
  )

  process.stdout.write(`${JSON.stringify({
    status: 'VERIFIED',
    nodeVersion: process.version,
    toolchainId: toolchain.descriptor.toolchainId,
    dependencyCount: Object.keys(toolchain.dependencyVersions).length,
    gatewayTestCount: testFiles.length,
    checkoutNodeModulesRequired: false,
  })}\n`)
} finally {
  rmSync(generatedConfig, { force: true })
}
