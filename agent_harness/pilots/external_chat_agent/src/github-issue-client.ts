import type {
  GenericModelClient,
  GenericModelGenerateRequest,
  GenericModelGenerateResponse,
} from '@agent-harness/generic-model-adapter'

const sleep = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms))
const REQUEST_PREFIX = '<!-- ET_TOOL_EXTERNAL_AGENT_REQUEST:'
const REQUEST_PART_PREFIX = '<!-- ET_TOOL_EXTERNAL_AGENT_REQUEST_PART:'
const RESPONSE_PREFIX = '<!-- ET_TOOL_EXTERNAL_AGENT_RESPONSE:'
const SAFE_COMMENT_BYTES = 60_000
const SAFE_CHUNK_PAYLOAD_BYTES = 50_000

interface GitHubIssueComment {
  readonly id: number
  readonly body?: string | null
  readonly user?: { readonly login?: string }
}

export interface GitHubIssueModelClientOptions {
  readonly token: string
  readonly repository: string
  readonly issueNumber: number
  readonly timeoutMs?: number
  readonly pollIntervalMs?: number
  readonly apiBaseUrl?: string
}

export interface ExternalAgentExchange {
  readonly requestId: string
  readonly purpose: GenericModelGenerateRequest['purpose']
  readonly requestCommentId: number
  readonly responseCommentId: number
  readonly responseAuthor?: string
}

export class GitHubIssueModelClient implements GenericModelClient {
  readonly clientId = 'external-chat-agent:github-issue-v0.1'
  readonly exchanges: ExternalAgentExchange[] = []

  private readonly timeoutMs: number
  private readonly pollIntervalMs: number
  private readonly apiBaseUrl: string

  constructor(private readonly options: GitHubIssueModelClientOptions) {
    if (!options.token.trim()) throw new Error('GitHub issue bridge token is required')
    if (!/^[-A-Za-z0-9_.]+\/[-A-Za-z0-9_.]+$/.test(options.repository)) {
      throw new Error('repository must be owner/name')
    }
    if (!Number.isInteger(options.issueNumber) || options.issueNumber <= 0) {
      throw new Error('issueNumber must be a positive integer')
    }
    this.timeoutMs = options.timeoutMs ?? 15 * 60_000
    this.pollIntervalMs = options.pollIntervalMs ?? 2_000
    this.apiBaseUrl = (options.apiBaseUrl ?? 'https://api.github.com').replace(/\/$/, '')
  }

  async generate(request: GenericModelGenerateRequest): Promise<GenericModelGenerateResponse> {
    const requestComments = await this.postRequest(request)
    const deadline = Date.now() + this.timeoutMs

    while (Date.now() < deadline) {
      const comments = await this.listComments()
      for (const comment of comments) {
        const response = this.parseResponse(comment, request)
        if (!response) continue
        this.exchanges.push({
          requestId: request.requestId,
          purpose: request.purpose,
          requestCommentId: requestComments[0].id,
          responseCommentId: comment.id,
          ...(comment.user?.login ? { responseAuthor: comment.user.login } : {}),
        })
        return response
      }
      await sleep(this.pollIntervalMs)
    }

    throw new Error(`Timed out waiting for external Agent response to ${request.purpose} request ${request.requestId}`)
  }

  private async postRequest(request: GenericModelGenerateRequest): Promise<GitHubIssueComment[]> {
    const bodies = this.renderRequestComments(request)
    const comments: GitHubIssueComment[] = []
    for (const body of bodies) comments.push(await this.postComment(body))
    return comments
  }

  private renderRequestComments(request: GenericModelGenerateRequest): string[] {
    const payload = JSON.stringify(request, null, 2)
    const body = `${REQUEST_PREFIX}${request.requestId} -->\n${payload}`
    if (Buffer.byteLength(body, 'utf8') <= SAFE_COMMENT_BYTES) return [body]

    const chunks = splitUtf8(payload, SAFE_CHUNK_PAYLOAD_BYTES)
    const total = chunks.length
    return chunks.map((chunk, index) => {
      const part = `${REQUEST_PART_PREFIX}${request.requestId}:${index + 1}/${total} -->\n${chunk}`
      if (Buffer.byteLength(part, 'utf8') > SAFE_COMMENT_BYTES) {
        throw new Error(`External Agent request chunk ${index + 1}/${total} for ${request.requestId} exceeds safe GitHub Issue comment size`)
      }
      return part
    })
  }

  private parseResponse(
    comment: GitHubIssueComment,
    request: GenericModelGenerateRequest,
  ): GenericModelGenerateResponse | undefined {
    const body = comment.body?.trim()
    if (!body) return undefined
    const marker = `${RESPONSE_PREFIX}${request.requestId} -->`
    if (!body.startsWith(marker)) return undefined

    const raw = body.slice(marker.length).trim()
    let parsed: GenericModelGenerateResponse
    try {
      parsed = JSON.parse(raw) as GenericModelGenerateResponse
    } catch (error) {
      throw new Error(`Invalid external Agent response JSON for ${request.requestId}: ${error instanceof Error ? error.message : String(error)}`)
    }

    if (parsed.contractVersion !== '0.1') throw new Error('External Agent response contractVersion must be 0.1')
    if (parsed.requestId !== request.requestId) throw new Error('External Agent response requestId mismatch')
    if (request.response.kind === 'TEXT' && !parsed.outputText?.trim()) {
      throw new Error('External Agent WORK response must contain non-empty outputText')
    }
    if (request.response.kind === 'JSON' && parsed.outputJson === undefined) {
      throw new Error('External Agent GOVERNANCE_REFLECTION response must contain outputJson')
    }

    return {
      ...parsed,
      providerId: parsed.providerId ?? 'chatgpt-conversation',
      modelId: parsed.modelId ?? 'external-chat-agent',
    }
  }

  private async postComment(body: string): Promise<GitHubIssueComment> {
    return await this.api<GitHubIssueComment>('POST', this.commentsPath(), { body })
  }

  private async listComments(): Promise<GitHubIssueComment[]> {
    const comments: GitHubIssueComment[] = []
    for (let page = 1; ; page += 1) {
      const batch = await this.api<GitHubIssueComment[]>('GET', `${this.commentsPath()}?per_page=100&page=${page}`)
      comments.push(...batch)
      if (batch.length < 100) return comments
    }
  }

  private commentsPath(): string {
    return `/repos/${this.options.repository}/issues/${this.options.issueNumber}/comments`
  }

  private async api<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.apiBaseUrl}${path}`, {
      method,
      headers: {
        accept: 'application/vnd.github+json',
        authorization: `Bearer ${this.options.token}`,
        'content-type': 'application/json',
        'user-agent': 'et-tool-external-chat-agent-pilot-v0.1',
        'x-github-api-version': '2022-11-28',
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    })
    const text = await response.text()
    if (!response.ok) {
      throw new Error(`GitHub mailbox ${method} ${path} failed (${response.status}): ${text.slice(0, 500)}`)
    }
    return (text ? JSON.parse(text) : undefined) as T
  }
}

function splitUtf8(input: string, maxBytes: number): string[] {
  if (!Number.isInteger(maxBytes) || maxBytes <= 0) throw new Error('maxBytes must be a positive integer')
  const chunks: string[] = []
  let current: string[] = []
  let currentBytes = 0

  for (const character of input) {
    const characterBytes = Buffer.byteLength(character, 'utf8')
    if (characterBytes > maxBytes) throw new Error('Single UTF-8 character exceeds chunk byte limit')
    if (currentBytes + characterBytes > maxBytes && current.length > 0) {
      chunks.push(current.join(''))
      current = []
      currentBytes = 0
    }
    current.push(character)
    currentBytes += characterBytes
  }

  if (current.length > 0) chunks.push(current.join(''))
  return chunks
}
