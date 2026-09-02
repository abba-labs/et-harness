import { assertExternalGatewayLauncher } from '../scripts/launcher-policy.mjs'
import { createGatewayServer } from './gateway.mjs'
import { GATEWAY_API } from './tools/health.mjs'

assertExternalGatewayLauncher()
const portOverride = process.env.ET_HARNESS_GATEWAY_PORT
const gateway = await createGatewayServer(
  portOverride === undefined ? {} : { port: Number.parseInt(portOverride, 10) },
)

try {
  const address = await gateway.listen()
  process.stderr.write(`${JSON.stringify({ event: 'gateway_started', api: GATEWAY_API, address })}\n`)
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
