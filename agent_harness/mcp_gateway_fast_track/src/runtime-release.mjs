import { createHash } from 'node:crypto'
import { readFile, realpath } from 'node:fs/promises'
import { isAbsolute, relative, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

import { environmentRoot } from '../scripts/environment-layout.mjs'

const RELEASE_SCHEMAS = new Set([
  'et-harness.pure-mcp-runtime-release.v1',
  'et-harness.pure-mcp-runtime-release.v2',
])
const POINTER_SCHEMA = 'et-harness.pure-mcp-active-release.v1'

const hashFile = async path => createHash('sha256').update(await readFile(path)).digest('hex')

const inside = (candidate, root) => {
  const relation = relative(root, candidate)
  return relation === '' || (!relation.startsWith('..') && !isAbsolute(relation))
}

const readJson = async path => JSON.parse(await readFile(path, 'utf8'))
const samePath = (left, right) => process.platform === 'win32'
  ? resolve(left).toLowerCase() === resolve(right).toLowerCase()
  : resolve(left) === resolve(right)

export const verifyRuntimeReleaseManifest = async (manifestPathInput, options = {}) => {
  if (!isAbsolute(manifestPathInput)) throw new Error('Runtime release manifest path must be absolute')
  const canonicalEnvironment = await realpath(options.environmentRoot ?? environmentRoot)
  const canonicalManifest = await realpath(manifestPathInput)
  if (!inside(canonicalManifest, canonicalEnvironment)) {
    throw new Error('Runtime release manifest escapes the ET Harness environment root')
  }

  const manifest = await readJson(canonicalManifest)
  if (!RELEASE_SCHEMAS.has(manifest?.schema)) {
    throw new Error('Runtime release manifest schema is invalid')
  }
  if (options.expectedSourceSignature !== undefined
      && manifest.sourceSignature !== options.expectedSourceSignature) {
    throw new Error(
      `Runtime release source signature mismatch: expected ${options.expectedSourceSignature}, received ${manifest.sourceSignature}`,
    )
  }
  if (options.expectedRepositoryRoot !== undefined
      && (!manifest.repositoryRoot || !samePath(manifest.repositoryRoot, options.expectedRepositoryRoot))) {
    throw new Error('Runtime release belongs to a different source workspace')
  }
  if (options.expectedToolchainId !== undefined
      && manifest.toolchainId !== options.expectedToolchainId) {
    throw new Error(
      `Runtime release Toolchain mismatch: expected ${options.expectedToolchainId}, received ${manifest.toolchainId ?? '<legacy>'}`,
    )
  }
  if (manifest.nodeVersion !== process.version) {
    throw new Error(`Runtime release requires ${manifest.nodeVersion}; current Node is ${process.version}`)
  }

  const releaseRoot = resolve(canonicalManifest, '..')
  const artifacts = manifest.artifacts ?? {}
  for (const [name, expectedHash] of Object.entries(artifacts)) {
    const path = resolve(releaseRoot, name)
    if (!inside(path, releaseRoot) || typeof expectedHash !== 'string' || await hashFile(path) !== expectedHash) {
      throw new Error(`Runtime release artifact failed integrity verification: ${name}`)
    }
  }

  const required = ['runtime.mjs', 'atp-project-plugin.mjs', 'deployment.json']
  if (manifest.schema === 'et-harness.pure-mcp-runtime-release.v2') {
    required.push('gateway.mjs', 'runtime-pointer.json', 'config/gateway.local.json')
  }
  for (const name of required) {
    if (typeof artifacts[name] !== 'string') {
      throw new Error(`Runtime release is missing required artifact: ${name}`)
    }
  }

  let gatewayConfigPath
  let runtimePointerPath
  if (manifest.schema === 'et-harness.pure-mcp-runtime-release.v2') {
    runtimePointerPath = resolve(releaseRoot, 'runtime-pointer.json')
    const localPointer = await readJson(runtimePointerPath)
    if (localPointer?.schema !== POINTER_SCHEMA
        || typeof localPointer.releaseManifestPath !== 'string'
        || !isAbsolute(localPointer.releaseManifestPath)
        || !samePath(localPointer.releaseManifestPath, canonicalManifest)) {
      throw new Error('Bundled Gateway Runtime pointer does not bind to its own release manifest')
    }
    gatewayConfigPath = resolve(releaseRoot, 'config', 'gateway.local.json')
    const gatewayConfig = await readJson(gatewayConfigPath)
    if (typeof gatewayConfig.runtimeReleasePointerPath !== 'string'
        || !isAbsolute(gatewayConfig.runtimeReleasePointerPath)
        || !samePath(gatewayConfig.runtimeReleasePointerPath, runtimePointerPath)) {
      throw new Error('Bundled Gateway configuration does not use its release-local Runtime pointer')
    }
  }

  return Object.freeze({
    manifest,
    manifestPath: canonicalManifest,
    releaseRoot,
    runtimeArtifactPath: resolve(releaseRoot, 'runtime.mjs'),
    deploymentConfigPath: resolve(releaseRoot, 'deployment.json'),
    ...(typeof artifacts['gateway.mjs'] === 'string'
      ? { gatewayArtifactPath: resolve(releaseRoot, 'gateway.mjs') }
      : {}),
    ...(gatewayConfigPath ? { gatewayConfigPath } : {}),
    ...(runtimePointerPath ? { runtimePointerPath } : {}),
  })
}

export const verifyRuntimeReleasePointer = async (pointerPath, options = {}) => {
  if (!isAbsolute(pointerPath)) throw new Error('Runtime release pointer must be an absolute path')
  const pointer = await readJson(pointerPath)
  if (pointer?.schema !== POINTER_SCHEMA
      || typeof pointer.releaseManifestPath !== 'string'
      || !isAbsolute(pointer.releaseManifestPath)) {
    throw new Error('Runtime release pointer is invalid')
  }
  return verifyRuntimeReleaseManifest(pointer.releaseManifestPath, options)
}

export const verifyActiveRuntimeRelease = verifyRuntimeReleasePointer

export const createFrozenRuntimeAccess = ({ releaseManifestPath, releasePointerPath }) => {
  if (!releaseManifestPath && !releasePointerPath) {
    throw new Error('Frozen Runtime access requires releaseManifestPath or releasePointerPath')
  }
  let loaded
  const runtimeModule = async () => {
    if (loaded) return loaded
    loaded = (async () => {
      const release = releaseManifestPath
        ? await verifyRuntimeReleaseManifest(releaseManifestPath)
        : await verifyRuntimeReleasePointer(releasePointerPath)
      const namespace = await import(pathToFileURL(release.runtimeArtifactPath).href)
      if (typeof namespace.createPureMcpRuntimeModule !== 'function') {
        throw new Error('Frozen Runtime artifact does not export createPureMcpRuntimeModule')
      }
      return namespace.createPureMcpRuntimeModule(release.deploymentConfigPath)
    })()
    return loaded
  }
  const portFor = async workspacePath =>
    (await runtimeModule()).createGovernanceHostRuntimePort({ cwd: workspacePath })
  const portForSnapshot = async snapshot => {
    const module = await runtimeModule()
    if (typeof module.ensureSupervisedTurn !== 'function') {
      throw new Error('Frozen Runtime artifact does not expose supervised Turn recovery')
    }
    await module.ensureSupervisedTurn({
      cwd: snapshot.workspacePath,
      runtimeId: snapshot.runtimeId,
      turnId: snapshot.turnId,
      taskId: snapshot.taskId,
      projectId: snapshot.projectId,
      projectRevision: snapshot.projectRevision,
      restoredRoute: snapshot.context?.route,
    })
    return module.createGovernanceHostRuntimePort({ cwd: snapshot.workspacePath })
  }

  return Object.freeze({
    async resolveProject(workspacePath) {
      return (await runtimeModule()).resolveProject(workspacePath)
    },
    async projectBootstrap(workspacePath) {
      const module = await runtimeModule()
      if (typeof module.projectBootstrap !== 'function') {
        throw new Error('Frozen Runtime artifact does not expose project Architecture bootstrap')
      }
      return module.projectBootstrap(workspacePath)
    },
    async openTurn(input) {
      return (await portFor(input.workspacePath)).openTurn(input)
    },
    async getStatus(snapshot) {
      const status = await (await portForSnapshot(snapshot)).getStatus(snapshot.runtimeId)
      if (!status?.supervision) throw new Error('Recovered Runtime Turn has no supervised status')
      return status
    },
    async observeWork(snapshot, input) {
      return (await portForSnapshot(snapshot)).observeWork(input)
    },
    async preflightAction(snapshot, input) {
      return (await portForSnapshot(snapshot)).preflightAction(input)
    },
    async closeTurn(snapshot, input) {
      const port = await portForSnapshot(snapshot)
      const status = await port.getStatus(snapshot.runtimeId)
      if (status?.supervision?.decision.status !== 'COMPLETE') {
        const taskEnd = await port.ingestExecutionEvent({
          runtimeId: snapshot.runtimeId,
          turnId: snapshot.turnId,
          eventId: `mcp-task-end-${createHash('sha256')
            .update(`${snapshot.runtimeId}\0${snapshot.turnId}`)
            .digest('hex')
            .slice(0, 32)}`,
          kind: 'TASK_END_REQUEST',
          payload: { requestedBy: 'pure-mcp-gateway' },
        })
        if (taskEnd.acceptance.status === 'REJECTED') {
          throw new Error(`Runtime rejected Gateway Task End request: ${taskEnd.acceptance.reasons.join('; ')}`)
        }
      }
      return port.closeTurn(input)
    },
    async abortTurn(snapshot, reason) {
      const module = await runtimeModule()
      if (typeof module.abortTurn !== 'function') {
        throw new Error('Frozen Runtime artifact does not expose failed-begin compensation')
      }
      return module.abortTurn({
        cwd: snapshot.workspacePath,
        runtimeId: snapshot.runtimeId,
        turnId: snapshot.turnId,
        taskId: snapshot.taskId,
        projectId: snapshot.projectId,
        projectRevision: snapshot.projectRevision,
        reason,
      })
    },
    async ingest(snapshot, input) {
      return (await portForSnapshot(snapshot)).ingestExecutionEvent(input)
    },
    async ingestTrustedValidationSpan(snapshot, input) {
      const module = await runtimeModule()
      if (typeof module.ingestTrustedValidationSpan !== 'function') {
        throw new Error('Frozen Runtime artifact does not expose trusted validation span ingress')
      }
      await module.ensureSupervisedTurn({
        cwd: snapshot.workspacePath,
        runtimeId: snapshot.runtimeId,
        turnId: snapshot.turnId,
        taskId: snapshot.taskId,
        projectId: snapshot.projectId,
        projectRevision: snapshot.projectRevision,
      })
      return module.ingestTrustedValidationSpan({ cwd: snapshot.workspacePath, ...input })
    },
    async close() {
      if (loaded) await (await loaded).close()
    },
  })
}
