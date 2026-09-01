import { createHash } from 'node:crypto'
import { readFile, realpath } from 'node:fs/promises'
import { isAbsolute, relative, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

import {
  computeRuntimeSourceSignature,
  environmentRoot,
  repositoryRoot,
} from '../scripts/runtime-bundle-inputs.mjs'

const hashFile = async (path) => createHash('sha256').update(await readFile(path)).digest('hex')

const inside = (candidate, root) => {
  const relation = relative(root, candidate)
  return relation === '' || (!relation.startsWith('..') && !isAbsolute(relation))
}

const readJson = async (path) => JSON.parse(await readFile(path, 'utf8'))

export const verifyActiveRuntimeRelease = async (pointerPath) => {
  if (!isAbsolute(pointerPath)) throw new Error('Runtime release pointer must be an absolute path')
  const pointer = await readJson(pointerPath)
  if (pointer?.schema !== 'et-harness.pure-mcp-active-release.v1'
      || typeof pointer.releaseManifestPath !== 'string'
      || !isAbsolute(pointer.releaseManifestPath)) {
    throw new Error('Runtime release pointer is invalid')
  }
  const canonicalEnvironment = await realpath(environmentRoot)
  const canonicalManifest = await realpath(pointer.releaseManifestPath)
  if (!inside(canonicalManifest, canonicalEnvironment)) {
    throw new Error('Runtime release manifest escapes the D-drive ET Harness environment')
  }
  const manifest = await readJson(canonicalManifest)
  if (manifest?.schema !== 'et-harness.pure-mcp-runtime-release.v1') {
    throw new Error('Runtime release manifest schema is invalid')
  }
  const expectedSignature = computeRuntimeSourceSignature()
  if (manifest.sourceSignature !== expectedSignature) {
    throw new Error(
      `Runtime release is stale for the current source: expected ${expectedSignature}, received ${manifest.sourceSignature}`,
    )
  }
  if (manifest.repositoryRoot?.toLowerCase() !== repositoryRoot.toLowerCase()) {
    throw new Error('Runtime release belongs to a different worktree')
  }
  if (manifest.nodeVersion !== process.version) {
    throw new Error(`Runtime release requires ${manifest.nodeVersion}; current Node is ${process.version}`)
  }
  const releaseRoot = resolve(canonicalManifest, '..')
  for (const [name, expectedHash] of Object.entries(manifest.artifacts ?? {})) {
    const path = resolve(releaseRoot, name)
    if (!inside(path, releaseRoot) || await hashFile(path) !== expectedHash) {
      throw new Error(`Runtime release artifact failed integrity verification: ${name}`)
    }
  }
  for (const required of ['runtime.mjs', 'atp-project-plugin.mjs', 'deployment.json']) {
    if (typeof manifest.artifacts?.[required] !== 'string') {
      throw new Error(`Runtime release is missing required artifact: ${required}`)
    }
  }
  return Object.freeze({
    manifest,
    releaseRoot,
    runtimeArtifactPath: resolve(releaseRoot, 'runtime.mjs'),
    deploymentConfigPath: resolve(releaseRoot, 'deployment.json'),
  })
}

export const createFrozenRuntimeAccess = ({ releasePointerPath }) => {
  let loaded
  const runtimeModule = async () => {
    if (loaded) return loaded
    loaded = (async () => {
      const release = await verifyActiveRuntimeRelease(releasePointerPath)
      const namespace = await import(pathToFileURL(release.runtimeArtifactPath).href)
      if (typeof namespace.createPureMcpRuntimeModule !== 'function') {
        throw new Error('Frozen Runtime artifact does not export createPureMcpRuntimeModule')
      }
      return namespace.createPureMcpRuntimeModule(release.deploymentConfigPath)
    })()
    return loaded
  }
  const portFor = async (workspacePath) =>
    (await runtimeModule()).createGovernanceHostRuntimePort({ cwd: workspacePath })
  const portForSnapshot = async (snapshot) => {
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
    })
    return module.createGovernanceHostRuntimePort({ cwd: snapshot.workspacePath })
  }

  return Object.freeze({
    async resolveProject(workspacePath) {
      return (await runtimeModule()).resolveProject(workspacePath)
    },
    async openTurn(input) {
      return (await portFor(input.workspacePath)).openTurn(input)
    },
    async getStatus(snapshot) {
      const status = await (await portForSnapshot(snapshot)).getStatus(snapshot.runtimeId)
      if (!status?.supervision) {
        throw new Error('Recovered Runtime Turn has no supervised status')
      }
      return status
    },
    async observeWork(snapshot, input) {
      return (await portForSnapshot(snapshot)).observeWork(input)
    },
    async preflightAction(snapshot, input) {
      return (await portForSnapshot(snapshot)).preflightAction(input)
    },
    async closeTurn(snapshot, input) {
      return (await portForSnapshot(snapshot)).closeTurn(input)
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
