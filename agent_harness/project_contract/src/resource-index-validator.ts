import type {
  ProjectResourceIndexV01,
  ProjectResourceInterfaceValidationResult,
  ProjectResourceKind,
} from './contracts.js'
import {
  expectedProjectResourceStandard,
  parseNumberedResourceFileName,
} from './resource-standards.js'

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isNonEmptyString = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0

export function validateProjectResourceIndex(
  kind: ProjectResourceKind,
  input: unknown,
  availableFiles?: readonly string[],
): ProjectResourceInterfaceValidationResult {
  const errors: string[] = []
  const warnings: string[] = []

  if (!isRecord(input)) {
    return { valid: false, errors: ['00_INDEX Front Matter 必须是对象'], warnings }
  }

  if (input.interface !== 'project-resource-index-v0.1') {
    errors.push('interface 必须为 project-resource-index-v0.1')
  }

  if (input.resource !== kind) {
    errors.push(`resource 必须为 ${kind}`)
  }

  const expectedStandard = expectedProjectResourceStandard(kind)
  if (input.standard !== expectedStandard) {
    errors.push(`standard 必须为 ${expectedStandard}`)
  }

  if (!Array.isArray(input.files)) {
    errors.push('files 必须是数组')
    return { valid: false, errors, warnings }
  }

  const seenIds = new Set<string>()
  const seenFiles = new Set<string>()

  for (const [index, entry] of input.files.entries()) {
    const path = `files[${index}]`
    if (!isRecord(entry)) {
      errors.push(`${path} 必须是对象`)
      continue
    }

    if (!isNonEmptyString(entry.file)) {
      errors.push(`${path}.file 不能为空`)
      continue
    }

    const parsed = parseNumberedResourceFileName(kind, entry.file)
    if (!parsed) {
      errors.push(`${path}.file 不符合编号文件规范`)
      continue
    }

    if (entry.id !== parsed.fileId) {
      errors.push(`${path}.id 必须为 ${parsed.fileId}`)
    }

    if (seenIds.has(parsed.fileId)) {
      errors.push(`File ID 重复: ${parsed.fileId}`)
    }
    seenIds.add(parsed.fileId)

    if (seenFiles.has(entry.file)) {
      errors.push(`Index 文件重复: ${entry.file}`)
    }
    seenFiles.add(entry.file)

    if (!isNonEmptyString(entry.title)) {
      errors.push(`${path}.title 不能为空`)
    }

    if (!isNonEmptyString(entry.summary)) {
      errors.push(`${path}.summary 不能为空`)
    } else if (entry.summary.length > 160) {
      warnings.push(`${path}.summary 过长；建议控制在一句话内`)
    }

    if (!Array.isArray(entry.aliases) || entry.aliases.some(alias => !isNonEmptyString(alias))) {
      errors.push(`${path}.aliases 必须是字符串数组`)
    } else if (entry.aliases.length === 0) {
      warnings.push(`${path}.aliases 为空；路由召回率可能降低`)
    }
  }

  if (availableFiles !== undefined) {
    const available = new Set(availableFiles)

    for (const file of seenFiles) {
      if (!available.has(file)) {
        errors.push(`Index 指向不存在文件: ${file}`)
      }
    }

    for (const file of availableFiles) {
      if (parseNumberedResourceFileName(kind, file) && !seenFiles.has(file)) {
        errors.push(`正式可路由文件未进入 00_INDEX: ${file}`)
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  }
}

export function assertProjectResourceIndex(
  kind: ProjectResourceKind,
  input: unknown,
  availableFiles?: readonly string[],
): asserts input is ProjectResourceIndexV01 {
  const result = validateProjectResourceIndex(kind, input, availableFiles)
  if (!result.valid) {
    throw new Error(`${kind} 项目接口拒绝接入: ${result.errors.join('; ')}`)
  }
}
