import { parse } from 'yaml'

export interface ParsedFrontMatter<T = unknown> {
  readonly data: T
  readonly body: string
}

const FRONT_MATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/

export function parseYamlFrontMatter<T = unknown>(text: string): ParsedFrontMatter<T> {
  const match = FRONT_MATTER_RE.exec(text)
  if (!match) {
    throw new Error('缺少合法 YAML Front Matter')
  }

  const yamlText = match[1] ?? ''
  let data: unknown
  try {
    data = parse(yamlText)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`YAML Front Matter 解析失败: ${message}`)
  }

  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    throw new Error('YAML Front Matter 必须解析为对象')
  }

  return {
    data: data as T,
    body: text.slice(match[0].length),
  }
}
