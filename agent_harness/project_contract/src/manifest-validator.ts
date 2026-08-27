import { isAbsolute } from 'node:path'
import type {
  ProjectManifestV01,
  ProjectManifestValidationResult,
  ProjectResourceKind,
} from './contracts.js'
import { expectedProjectResourceStandard } from './resource-standards.js'

const PROJECT_ID_RE = /^[a-z0-9][a-z0-9._-]{1,63}$/
const REQUIRED_RESOURCES: readonly ProjectResourceKind[] = [
  'architecture',
  'rules',
  'knowledge',
  'gates',
]

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isSafeRelativePath = (value: string): boolean => {
  if (!value.trim() || isAbsolute(value)) return false
  const segments = value.replaceAll('\\', '/').split('/')
  return !segments.some(segment => segment === '..')
}

export function validateProjectManifest(input: unknown): ProjectManifestValidationResult {
  const errors: string[] = []

  if (!isRecord(input)) return { valid: false, errors: ['manifest 必须是对象'] }

  if (input.contract_version !== '0.1') {
    errors.push('contract_version 必须为 0.1')
  }

  const project = input.project
  if (!isRecord(project)) {
    errors.push('project 必须是对象')
  } else {
    if (typeof project.id !== 'string' || !PROJECT_ID_RE.test(project.id)) {
      errors.push('project.id 非法；只允许小写字母、数字、点、下划线和连字符')
    }
    if (typeof project.name !== 'string' || !project.name.trim()) {
      errors.push('project.name 不能为空')
    }
    if (project.aliases !== undefined) {
      if (!Array.isArray(project.aliases) || project.aliases.some(item => typeof item !== 'string' || !item.trim())) {
        errors.push('project.aliases 必须是非空字符串数组')
      }
    }
  }

  const root = input.root
  if (!isRecord(root) || !Array.isArray(root.markers) || root.markers.length === 0) {
    errors.push('root.markers 至少需要一个项目根标记')
  } else if (root.markers.some(item => typeof item !== 'string' || !isSafeRelativePath(item))) {
    errors.push('root.markers 必须是安全的相对路径')
  }

  const resources = input.resources
  if (!isRecord(resources)) {
    errors.push('resources 必须是对象')
  } else {
    for (const kind of REQUIRED_RESOURCES) {
      const source = resources[kind]
      if (!isRecord(source)) {
        errors.push(`resources.${kind} 必须是对象`)
        continue
      }

      if (typeof source.path !== 'string' || !isSafeRelativePath(source.path)) {
        errors.push(`resources.${kind}.path 必须是安全的相对路径`)
      }

      const expectedStandard = expectedProjectResourceStandard(kind)
      if (source.standard !== expectedStandard) {
        errors.push(`resources.${kind}.standard 必须为 ${expectedStandard}`)
      }
    }
  }

  const adapters = input.adapters
  if (adapters !== undefined) {
    if (!isRecord(adapters)) {
      errors.push('adapters 必须是对象')
    } else {
      for (const [name, adapter] of Object.entries(adapters)) {
        if (!isRecord(adapter) || typeof adapter.provider !== 'string' || !adapter.provider.trim()) {
          errors.push(`adapters.${name}.provider 不能为空`)
        }
      }
    }
  }

  return { valid: errors.length === 0, errors }
}

export function assertProjectManifest(input: unknown): asserts input is ProjectManifestV01 {
  const result = validateProjectManifest(input)
  if (!result.valid) {
    throw new Error(`Project Contract v0.1 校验失败: ${result.errors.join('; ')}`)
  }
}
