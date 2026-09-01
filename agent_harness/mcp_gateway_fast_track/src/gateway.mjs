import { randomUUID } from 'node:crypto'
import { createServer as createHttpServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { isAbsolute, resolve } from 'node:path'

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { isInitializeRequest } from '@modelcontextprotocol/sdk/types.js'
import { z } from 'zod'

import {
  createGatewayProcessHealth,
  createHealthResult,
  GATEWAY_API,
  GATEWAY_VERSION,
} from './tools/health.mjs'
import { assertExternalGatewayLauncher } from '../scripts/launcher-policy.mjs'
import {
  createFileSnapshotStore,
  createGovernanceController,
  governanceToolError,
} from './governance.mjs'
import { createFrozenRuntimeAccess } from './runtime-release.mjs'
import {
  createTrustedCheckpointController,
  registerTrustedCheckpointTools,
} from './trusted-checkpoint.mjs'

export const MCP_INSTRUCTIONS =
  'For governed work, call harness_begin first. Read required filesystem mustRead only with harness_read_required. Follow ruleOwners/writeScope; use harness_observe for facts and harness_preflight before mutations. Use harness_checkpoint to run frozen validations and emit trusted evidence. Query harness_status, then harness_complete with truthful reflection. Never submit PASS, receipts, provider IDs, commands, raw events, or self-declare COMPLETE. Do not expose Runtime, Ledger, auth, or raw Closure data.'

const CONFIG_URL = new URL('../config/gateway.local.json', import.meta.url)

const sendJson = (response, statusCode, body, extraHeaders = {}) => {
  if (response.headersSent) return
  response.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    ...extraHeaders,
  })
  response.end(JSON.stringify(body))
}

const sendRpcError = (response, statusCode, code, message) =>
  sendJson(response, statusCode, {
    jsonrpc: '2.0',
    error: { code, message },
    id: null,
  })

const readBoundedJson = async (request, response, maxRequestBytes) => {
  const contentLength = Number(request.headers['content-length'] ?? 0)
  if (Number.isFinite(contentLength) && contentLength > maxRequestBytes) {
    request.resume()
    sendRpcError(response, 413, -32600, 'Request body exceeds the configured limit')
    return undefined
  }

  const chunks = []
  let size = 0
  for await (const chunk of request) {
    size += chunk.length
    if (size > maxRequestBytes) {
      request.resume()
      sendRpcError(response, 413, -32600, 'Request body exceeds the configured limit')
      return undefined
    }
    chunks.push(chunk)
  }

  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8'))
  } catch {
    sendRpcError(response, 400, -32700, 'Invalid JSON request body')
    return undefined
  }
}

const toolResult = (value, isError = false) => ({
  ...(isError ? { isError: true } : {}),
  content: [{ type: 'text', text: JSON.stringify(value) }],
  structuredContent: value,
})

const createProtocolServer = (governance) => {
  const server = new McpServer(
    {
      name: 'et-harness-mcp-fast-track',
      version: GATEWAY_VERSION,
    },
    {
      instructions: MCP_INSTRUCTIONS,
    },
  )

  server.registerTool(
    'harness_health',
    {
      title: 'ET Harness health',
      description:
        'Return the bounded readiness state of the ET Harness MCP Gateway. This Round 1 tool does not begin a project task or claim Runtime connectivity.',
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async () => {
      return toolResult(createHealthResult(governance.health()))
    },
  )

  server.registerTool(
    'harness_begin',
    {
      title: 'Begin an ET Harness governed task',
      description:
        'Resolve workspacePath to a configured project, open one existing Runtime Turn, invoke the existing Project Context Contributor, and return bounded structured Task Context.',
      inputSchema: {
        workspacePath: z.string().min(1).max(1024),
        intent: z.string().min(1).max(8000),
        requestedTaskId: z.string().min(1).max(160).optional(),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (input) => {
      try {
        return toolResult(await governance.begin(input))
      } catch (error) {
        return toolResult(governanceToolError(error), true)
      }
    },
  )

  server.registerTool(
    'harness_status',
    {
      title: 'Read ET Harness governed task status',
      description:
        'Return a bounded status summary for a task previously opened with harness_begin. Does not expose raw Runtime or Ledger state.',
      inputSchema: { taskId: z.string().min(1).max(160) },
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (input) => {
      try {
        return toolResult(await governance.status(input))
      } catch (error) {
        return toolResult(governanceToolError(error), true)
      }
    },
  )

  server.registerTool(
    'harness_observe',
    {
      title: 'Submit governed work observation',
      description:
        'Forward one bounded, source-backed work observation to the existing Governance Runtime for a task opened with harness_begin.',
      inputSchema: {
        taskId: z.string().min(1).max(160),
        kind: z.enum(['tool-result', 'resource-touch', 'assistant-message', 'user-message']),
        name: z.string().min(1).max(256).optional(),
        arguments: z.unknown().optional(),
        isError: z.boolean().optional(),
        eventRef: z.string().min(1).max(2048).optional(),
        resourceRefs: z.array(z.string().min(1).max(2048)).max(64).optional(),
        summary: z.string().min(1).max(8000).optional(),
        messageRefs: z.array(z.string().min(1).max(2048)).max(64).optional(),
        text: z.string().min(1).max(8000).optional(),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
    },
    async (input) => {
      try {
        return toolResult(await governance.observe(input))
      } catch (error) {
        return toolResult(governanceToolError(error), true)
      }
    },
  )

  server.registerTool(
    'harness_preflight',
    {
      title: 'Preflight a governed action',
      description:
        'Ask the existing Governance Runtime whether one read-only or mutating action is allowed before executing it.',
      inputSchema: {
        taskId: z.string().min(1).max(160),
        name: z.string().min(1).max(256),
        arguments: z.unknown().optional(),
        eventRef: z.string().min(1).max(2048).optional(),
        effect: z.union([
          z.object({ kind: z.literal('READ_ONLY') }),
          z.object({
            kind: z.literal('MUTATION'),
            intent: z.object({
              resourceId: z.string().min(1).max(2048),
              path: z.string().min(1).max(1024).optional(),
              action: z.enum(['CREATE', 'UPDATE', 'DELETE', 'MOVE', 'COPY']),
            }),
          }),
        ]),
      },
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (input) => {
      try {
        return toolResult(await governance.preflight(input))
      } catch (error) {
        return toolResult(governanceToolError(error), true)
      }
    },
  )

  server.registerTool(
    'harness_complete',
    {
      title: 'Request governed Turn closure',
      description:
        'Forward a bounded Reflection proposal and candidate references through the existing Runtime closure path. Runtime remains the only completion authority.',
      inputSchema: {
        taskId: z.string().min(1).max(160),
        assistantMessageRefs: z.array(z.string().min(1).max(2048)).max(64).optional(),
        publicCandidateRefs: z.array(z.string().min(1).max(2048)).max(64).optional(),
        projectCandidateRefs: z.array(z.string().min(1).max(2048)).max(64).optional(),
        semanticReflection: z.record(z.string(), z.unknown()).optional(),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (input) => {
      try {
        return toolResult(await governance.complete(input))
      } catch (error) {
        return toolResult(governanceToolError(error), true)
      }
    },
  )

  registerTrustedCheckpointTools({
    server,
    governance,
    toolResult,
    governanceToolError,
  })

  return server
}

const normalizeOptions = async (overrides) => {
  const configured = JSON.parse(await readFile(CONFIG_URL, 'utf8'))
  const options = { ...configured, ...overrides }

  if (options.host !== '127.0.0.1') {
    throw new Error('ET Harness MCP Gateway may only bind to 127.0.0.1')
  }
  if (!Number.isInteger(options.port) || options.port < 0 || options.port > 65535) {
    throw new Error('Gateway port must be an integer from 0 through 65535')
  }
  if (options.path !== '/mcp') {
    throw new Error('Gateway MCP path must remain /mcp')
  }
  if (!Number.isInteger(options.maxRequestBytes) || options.maxRequestBytes < 1024) {
    throw new Error('Gateway request limit must be a bounded positive integer')
  }
  for (const field of ['runtimeReleasePointerPath', 'taskSnapshotRoot']) {
    if (typeof options[field] !== 'string' || !isAbsolute(options[field])) {
      throw new Error(`${field} must be an absolute path`)
    }
  }
  if (!Array.isArray(options.projects) || options.projects.some((item) => typeof item !== 'string')) {
    throw new Error('projects must be an array of project ids')
  }

  return Object.freeze(options)
}

export const createGatewayServer = async (overrides = {}) => {
  const { governanceController, ...optionOverrides } = overrides
  const options = await normalizeOptions(optionOverrides)
  let governance = governanceController
  let runtimeAccess
  if (!governance) {
    runtimeAccess = createFrozenRuntimeAccess({
      releasePointerPath: options.runtimeReleasePointerPath,
    })
    const base = createGovernanceController({
      runtimeAccess,
      snapshotStore: createFileSnapshotStore(options.taskSnapshotRoot),
      projects: options.projects,
    })
    const trusted = createTrustedCheckpointController({
      runtimeAccess,
      taskSnapshotRoot: options.taskSnapshotRoot,
    })
    governance = Object.freeze({ ...base, ...trusted })
  }
  const transports = new Map()
  const protocolServers = new Map()

  const closeSession = async (sessionId) => {
    transports.delete(sessionId)
    const server = protocolServers.get(sessionId)
    protocolServers.delete(sessionId)
    if (server) await server.close()
  }

  const handleMcpRequest = async (request, response, requestUrl) => {
    if (requestUrl.pathname !== options.path) {
      sendRpcError(response, 404, -32601, 'MCP endpoint not found')
      return
    }

    let body
    if (request.method === 'POST') {
      body = await readBoundedJson(request, response, options.maxRequestBytes)
      if (body === undefined) return
    }

    const sessionHeader = request.headers['mcp-session-id']
    const sessionId = Array.isArray(sessionHeader) ? sessionHeader[0] : sessionHeader
    let transport = sessionId ? transports.get(sessionId) : undefined

    if (!transport && request.method === 'POST' && !sessionId && isInitializeRequest(body)) {
      const protocolServer = createProtocolServer(governance)
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: randomUUID,
        enableJsonResponse: true,
        onsessioninitialized: (initializedSessionId) => {
          transports.set(initializedSessionId, transport)
          protocolServers.set(initializedSessionId, protocolServer)
        },
        onsessionclosed: (closedSessionId) => {
          void closeSession(closedSessionId)
        },
      })
      await protocolServer.connect(transport)
    } else if (!transport) {
      sendRpcError(response, 400, -32000, 'No valid MCP session was provided')
      return
    }

    await transport.handleRequest(request, response, body)
  }

  const handleHttpRequest = async (request, response) => {
    const requestUrl = new URL(request.url ?? '/', `http://${options.host}`)
    if (requestUrl.pathname === '/health') {
      if (request.method !== 'GET') {
        sendJson(
          response,
          405,
          { status: 'METHOD_NOT_ALLOWED' },
          { allow: 'GET' },
        )
        return
      }
      sendJson(response, 200, createGatewayProcessHealth())
      return
    }
    await handleMcpRequest(request, response, requestUrl)
  }

  const httpServer = createHttpServer((request, response) => {
    void handleHttpRequest(request, response).catch((error) => {
      process.stderr.write(
        `${JSON.stringify({ event: 'mcp_request_failed', message: error instanceof Error ? error.message : 'Unknown error' })}\n`,
      )
      sendRpcError(response, 500, -32603, 'Internal MCP Gateway error')
    })
  })

  const listen = async () =>
    new Promise((resolveListen, rejectListen) => {
      const onError = (error) => rejectListen(error)
      httpServer.once('error', onError)
      httpServer.listen(options.port, options.host, () => {
        httpServer.off('error', onError)
        resolveListen(httpServer.address())
      })
    })

  const close = async () => {
    const sessions = [...transports.keys()]
    await Promise.allSettled(sessions.map(closeSession))
    if (!httpServer.listening) return
    await new Promise((resolveClose, rejectClose) =>
      httpServer.close((error) => (error ? rejectClose(error) : resolveClose())),
    )
    await runtimeAccess?.close()
  }

  return Object.freeze({
    options,
    listen,
    close,
    address: () => httpServer.address(),
  })
}

const isMainModule = () => {
  if (!process.argv[1]) return false
  return resolve(process.argv[1]).toLowerCase() === resolve(fileURLToPath(import.meta.url)).toLowerCase()
}

if (isMainModule()) {
  assertExternalGatewayLauncher()
  const portOverride = process.env.ET_HARNESS_GATEWAY_PORT
  const gateway = await createGatewayServer(
    portOverride === undefined ? {} : { port: Number.parseInt(portOverride, 10) },
  )

  try {
    const address = await gateway.listen()
    process.stderr.write(
      `${JSON.stringify({ event: 'gateway_started', api: GATEWAY_API, address })}\n`,
    )
  } catch (error) {
    process.stderr.write(
      `${JSON.stringify({ event: 'gateway_start_failed', message: error instanceof Error ? error.message : 'Unknown error' })}\n`,
    )
    process.exitCode = 1
  }

  const shutdown = async () => {
    await gateway.close()
    process.exit(0)
  }
  process.once('SIGINT', () => void shutdown())
  process.once('SIGTERM', () => void shutdown())
}
