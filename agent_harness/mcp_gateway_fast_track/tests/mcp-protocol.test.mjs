import assert from 'node:assert/strict'
import { test } from 'node:test'

import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'

import { createGatewayServer, MCP_INSTRUCTIONS } from '../src/gateway.mjs'

const withGatewayClient = async (callback) => {
  const gateway = await createGatewayServer({ port: 0 })
  const address = await gateway.listen()
  assert.equal(address.address, '127.0.0.1')
  const client = new Client({ name: 'et-harness-protocol-test', version: '0.1.0' })
  const transport = new StreamableHTTPClientTransport(
    new URL(`http://127.0.0.1:${address.port}/mcp`),
  )

  try {
    await client.connect(transport)
    await callback({ gateway, address, client })
  } finally {
    await client.close()
    await gateway.close()
  }
}

test('T1 rejects non-loopback binding and listens only on 127.0.0.1', async () => {
  await assert.rejects(
    createGatewayServer({ host: '0.0.0.0', port: 0 }),
    /may only bind to 127\.0\.0\.1/,
  )
  await withGatewayClient(async ({ address }) => assert.equal(address.address, '127.0.0.1'))
})

test('T1b GET /health reports only Gateway process health', async () => {
  const gateway = await createGatewayServer({ port: 0 })
  const address = await gateway.listen()
  try {
    const response = await fetch(`http://127.0.0.1:${address.port}/health`)
    assert.equal(response.status, 200)
    const body = await response.json()
    assert.deepEqual(Object.keys(body).sort(), [
      'gatewayApi',
      'gatewayVersion',
      'processId',
      'service',
      'status',
      'uptimeSeconds',
    ])
    assert.equal(body.status, 'UP')
    assert.equal(body.service, 'et-harness-mcp-gateway')
    assert.equal(body.processId, process.pid)
    assert.equal(Number.isInteger(body.uptimeSeconds), true)
    assert.equal('runtimeConnected' in body, false)
    assert.equal('projects' in body, false)
  } finally {
    await gateway.close()
  }
})

test('T2-T3 initialize exposes fixed identity and self-contained instructions', async () => {
  await withGatewayClient(async ({ client }) => {
    assert.deepEqual(client.getServerVersion(), {
      name: 'et-harness-mcp-fast-track',
      version: '0.1.0',
    })
    assert.equal(client.getInstructions(), MCP_INSTRUCTIONS)
    assert.ok(MCP_INSTRUCTIONS.length <= 512)
  })
})

test('T4 tools/list exposes the frozen Round 2 tool set', async () => {
  await withGatewayClient(async ({ client }) => {
    const listed = await client.listTools()
    assert.deepEqual(
      listed.tools.map((tool) => tool.name),
      ['harness_health', 'harness_begin', 'harness_status'],
    )
  })
})

test('T5 harness_health returns an honest bounded Round 1 result', async () => {
  await withGatewayClient(async ({ client }) => {
    const result = await client.callTool({ name: 'harness_health', arguments: {} })
    assert.deepEqual(result.structuredContent, {
      status: 'READY',
      gatewayVersion: '0.1.0',
      gatewayApi: 'et-harness-mcp-fast-track.v1',
      runtimePortVersion: '0.1',
      runtimeConnected: false,
      projects: ['et-automated-testing-platform'],
    })
  })
})

test('T6 unknown tools return the standard method-not-found error', async () => {
  await withGatewayClient(async ({ client }) => {
    const result = await client.callTool({
      name: 'not_a_harness_tool',
      arguments: {},
    })
    assert.equal(result.isError, true)
    assert.match(
      result.content.find((item) => item.type === 'text')?.text ?? '',
      /Tool not_a_harness_tool not found/,
    )
  })
})

test('T7 oversized requests are rejected before MCP dispatch', async () => {
  const gateway = await createGatewayServer({ port: 0, maxRequestBytes: 1024 })
  const address = await gateway.listen()
  try {
    const response = await fetch(`http://127.0.0.1:${address.port}/mcp`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ payload: 'x'.repeat(2048) }),
    })
    assert.equal(response.status, 413)
    const body = await response.json()
    assert.equal(body.error.code, -32600)
  } finally {
    await gateway.close()
  }
})
