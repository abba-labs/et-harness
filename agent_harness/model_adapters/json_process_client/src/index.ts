import { spawn } from 'node:child_process'
import type {
  GenericModelClient,
  GenericModelGenerateRequest,
  GenericModelGenerateResponse,
} from '@agent-harness/generic-model-adapter'

export interface JsonProcessModelClientConfig {
  readonly clientId: string
  readonly command: string
  readonly args?: readonly string[]
  readonly cwd?: string
  readonly env?: Readonly<Record<string, string>>
  readonly timeoutMs?: number
  readonly maxOutputBytes?: number
}

const DEFAULT_TIMEOUT_MS = 120_000
const DEFAULT_MAX_OUTPUT_BYTES = 4 * 1024 * 1024
const SAFE_PARENT_ENV = /^(?:PATH|HOME|USERPROFILE|SYSTEMROOT|WINDIR|COMSPEC|PATHEXT|TMP|TEMP|TMPDIR|LANG|LC_ALL|LC_CTYPE|HTTP_PROXY|HTTPS_PROXY|NO_PROXY|ALL_PROXY)$/i

const positive = (value: number | undefined, fallback: number): number =>
  Number.isFinite(value) && Number(value) > 0 ? Number(value) : fallback

const safeParentEnv = (): Record<string, string> => {
  const env: Record<string, string> = {}
  for (const [key, value] of Object.entries(process.env)) {
    if (value !== undefined && SAFE_PARENT_ENV.test(key)) env[key] = value
  }
  return env
}

export class JsonProcessModelClient implements GenericModelClient {
  readonly clientId: string
  private readonly command: string
  private readonly args: readonly string[]
  private readonly cwd: string | undefined
  private readonly env: Readonly<Record<string, string>>
  private readonly timeoutMs: number
  private readonly maxOutputBytes: number

  constructor(config: JsonProcessModelClientConfig) {
    this.clientId = config.clientId.trim()
    if (!this.clientId) throw new Error('JsonProcessModelClient clientId cannot be empty')
    this.command = config.command.trim()
    if (!this.command) throw new Error('JsonProcessModelClient command cannot be empty')
    this.args = [...(config.args ?? [])]
    this.cwd = config.cwd?.trim() || undefined
    this.env = { ...(config.env ?? {}) }
    this.timeoutMs = positive(config.timeoutMs, DEFAULT_TIMEOUT_MS)
    this.maxOutputBytes = positive(config.maxOutputBytes, DEFAULT_MAX_OUTPUT_BYTES)
  }

  async generate(request: GenericModelGenerateRequest): Promise<GenericModelGenerateResponse> {
    const stdout = await this.runProcess(request)
    const text = stdout.trim()
    if (!text) throw new Error('JSON process model bridge returned empty stdout')
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch (error) {
      throw new Error(
        `JSON process model bridge stdout is not one JSON object: ${error instanceof Error ? error.message : String(error)}`,
      )
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('JSON process model bridge response must be an object')
    }
    return parsed as GenericModelGenerateResponse
  }

  private runProcess(request: GenericModelGenerateRequest): Promise<string> {
    return new Promise((resolve, reject) => {
      const child = spawn(this.command, this.args, {
        ...(this.cwd ? { cwd: this.cwd } : {}),
        env: { ...safeParentEnv(), ...this.env },
        shell: false,
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      })
      const stdout: Buffer[] = []
      const stderr: Buffer[] = []
      let stdoutBytes = 0
      let stderrBytes = 0
      let settled = false
      let timer: NodeJS.Timeout | undefined

      const finish = (error?: Error, value?: string): void => {
        if (settled) return
        settled = true
        if (timer) clearTimeout(timer)
        if (error) reject(error)
        else resolve(value ?? '')
      }

      const overflow = (stream: 'stdout' | 'stderr'): void => {
        child.kill()
        finish(new Error(`JSON process model bridge ${stream} exceeded ${this.maxOutputBytes} bytes`))
      }

      child.stdout.on('data', chunk => {
        const buffer = Buffer.from(chunk)
        stdoutBytes += buffer.length
        if (stdoutBytes > this.maxOutputBytes) return overflow('stdout')
        stdout.push(buffer)
      })
      child.stderr.on('data', chunk => {
        const buffer = Buffer.from(chunk)
        stderrBytes += buffer.length
        if (stderrBytes > this.maxOutputBytes) return overflow('stderr')
        stderr.push(buffer)
      })
      child.on('error', error => finish(error))
      child.on('close', code => {
        if (settled) return
        const stderrText = Buffer.concat(stderr).toString('utf8').trim()
        if (code !== 0) {
          finish(new Error(
            `JSON process model bridge exited with code ${String(code)}${stderrText ? `: ${stderrText}` : ''}`,
          ))
          return
        }
        finish(undefined, Buffer.concat(stdout).toString('utf8'))
      })

      timer = setTimeout(() => {
        child.kill()
        finish(new Error(`JSON process model bridge timed out after ${this.timeoutMs} ms`))
      }, this.timeoutMs)
      timer.unref?.()

      child.stdin.on('error', error => finish(error))
      child.stdin.end(`${JSON.stringify(request)}\n`)
    })
  }
}

export default JsonProcessModelClient
