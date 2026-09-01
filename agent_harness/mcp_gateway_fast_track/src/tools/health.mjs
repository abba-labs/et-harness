export const GATEWAY_VERSION = '0.1.0'
export const GATEWAY_API = 'et-harness-mcp-fast-track.v1'

export const createGatewayProcessHealth = () => ({
  status: 'UP',
  service: 'et-harness-mcp-gateway',
  gatewayVersion: GATEWAY_VERSION,
  gatewayApi: GATEWAY_API,
  processId: process.pid,
  uptimeSeconds: Math.floor(process.uptime()),
})

export const createHealthResult = ({ runtimeConnected = false, projects = [] } = {}) => ({
  status: 'READY',
  gatewayVersion: GATEWAY_VERSION,
  gatewayApi: GATEWAY_API,
  runtimePortVersion: '0.1',
  runtimeConnected,
  projects,
})
