import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'

const url = new URL(process.env.ET_HARNESS_MCP_URL ?? 'http://127.0.0.1:8765/mcp')
const client = new Client({ name: 'et-harness-direct-smoke', version: '0.1.0' })
const transport = new StreamableHTTPClientTransport(url)

try {
  await client.connect(transport)
  const tools = await client.listTools()
  const health = await client.callTool({ name: 'harness_health', arguments: {} })
  process.stdout.write(
    `${JSON.stringify({
      serverInfo: client.getServerVersion(),
      instructionsPresent: Boolean(client.getInstructions()),
      tools: tools.tools.map((tool) => tool.name),
      health: health.structuredContent,
    })}\n`,
  )
} finally {
  await client.close()
}
