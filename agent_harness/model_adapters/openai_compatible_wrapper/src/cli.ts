#!/usr/bin/env node

import {
  configFromEnv,
  generateViaOpenAICompatible,
  validateGenericRequest,
} from './index.js'

const readStdin = async (): Promise<string> => {
  let text = ''
  process.stdin.setEncoding('utf8')
  for await (const chunk of process.stdin) text += chunk
  return text
}

const main = async (): Promise<void> => {
  const raw = await readStdin()
  if (!raw.trim()) throw new Error('Generic model request stdin is empty')
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch (error) {
    throw new Error(`Generic model request stdin is not JSON: ${error instanceof Error ? error.message : String(error)}`)
  }
  const request = validateGenericRequest(parsed)
  const config = configFromEnv()
  const response = await generateViaOpenAICompatible(request, config)
  process.stdout.write(`${JSON.stringify(response)}\n`)
}

main().catch(error => {
  const message = error instanceof Error ? error.message : String(error)
  process.stderr.write(`[openai-compatible-model-wrapper] ${message}\n`)
  process.exitCode = 1
})
