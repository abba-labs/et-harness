import { randomUUID } from 'node:crypto'
import { createServer as createHttpServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { isInitializeRequest } from '@modelcontextprotocol/sdk/types.js'

import {
  createGatewayProcessHealth,
  createHealthResult,
  GATEWAY_API,
  GATEWAY_VERSION,
} from './tools/health.mjs'
import { assertExternalGatewayLauncher } from '../scripts/launcher-policy.mjs'

export const MCP_INSTRUCTIONS =
  'For every non-trivial task in a configured workspace, call harness_begin before project analysis or modification. Follow the returned mustRead, ruleOwners, writeScope, validation, and knownConflicts. Submit material source facts and conflicts through harness_observe. Query harness_status before claiming completion. Call harness_complete; the model must not self-declare PASS or COMPLETE. Do not expose internal Runtime, Ledger, auth, or raw Closure data.'

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

const createProtocolServer = () => {
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
      const result = createHealthResult()
      return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
        structuredContent: result,
      }
    },
  )

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

  return Object.freeze(options)
}

export const createGatewayServer = async (overrides = {}) => {
  const options = await normalizeOptions(overrides)
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
      const protocolServer = createProtocolServer()
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
