import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import {
  createProjectContext,
  findProjectRoot,
  getProjectResourceRoutingSpec,
  isValidResourceNodeId,
  parseNumberedResourceFileName,
  resolveProjectResourcePath,
  validateProjectManifest,
  validateProjectResourceIndex,
} from '../src/index.js'

const manifest = {
  contract_version: '0.1',
  project: {
    id: 'example-project',
    name: 'Example Project',
    type: 'software',
    aliases: ['example'],
  },
  root: {
    markers: ['src/main.ts'],
  },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {},
} as const

describe('Project Contract v0.1', () => {
  it('接受最小合法 manifest', () => {
    expect(validateProjectManifest(manifest)).toEqual({ valid: true, errors: [] })
  })

  it('拒绝绝对路径和目录穿越', () => {
    const invalid = {
      ...manifest,
      resources: {
        ...manifest.resources,
        rules: { path: '../rules', standard: 'rule-v0.1' },
      },
    }
    const result = validateProjectManifest(invalid)
    expect(result.valid).toBe(false)
    expect(result.errors.some(item => item.includes('resources.rules.path'))).toBe(true)
  })

  it('拒绝项目自行声明不兼容的资源接口标准', () => {
    const invalid = {
      ...manifest,
      resources: {
        ...manifest.resources,
        rules: { path: 'rules/', standard: 'architecture-v0.1' },
      },
    }
    const result = validateProjectManifest(invalid)
    expect(result.valid).toBe(false)
    expect(result.errors).toContain('resources.rules.standard 必须为 rule-v0.1')
  })

  it('生成与项目实现无关的 Resource Handle 与标准版本', () => {
    const context = createProjectContext(manifest, '/repo/example')
    expect(context.projectId).toBe('example-project')
    expect(context.resources).toEqual({
      architecture: 'project://example-project/architecture',
      rules: 'project://example-project/rules',
      knowledge: 'project://example-project/knowledge',
      gates: 'project://example-project/gates',
    })
    expect(context.resourceStandards).toEqual({
      architecture: 'architecture-v0.1',
      rules: 'rule-v0.1',
      knowledge: 'knowledge-v0.1',
      gates: 'gate-v0.1',
    })
  })

  it('通用 root locator 不依赖 ET-TOOL 目录', () => {
    const root = mkdtempSync(join(tmpdir(), 'project-contract-'))
    mkdirSync(join(root, 'src'), { recursive: true })
    mkdirSync(join(root, 'deep', 'nested'), { recursive: true })
    writeFileSync(join(root, 'src', 'main.ts'), 'export {}\n')

    expect(findProjectRoot(['src/main.ts'], join(root, 'deep', 'nested'))).toBe(root)
  })

  it('解析项目私有资源真实路径时只使用 manifest + project root', () => {
    expect(resolveProjectResourcePath(manifest, '/repo/example/', 'rules')).toBe(
      resolve('/repo/example', 'rules'),
    )
  })

  it('所有项目资源共享 00_INDEX + 固定 Node 前缀的寻址模型', () => {
    expect(getProjectResourceRoutingSpec('architecture')).toMatchObject({
      indexFile: '00_INDEX.md',
      nodePrefix: 'A',
      fileExtension: 'md',
    })
    expect(getProjectResourceRoutingSpec('rules')).toMatchObject({
      indexFile: '00_INDEX.md',
      nodePrefix: 'R',
      fileExtension: 'md',
    })
    expect(getProjectResourceRoutingSpec('knowledge')).toMatchObject({
      indexFile: '00_INDEX.md',
      nodePrefix: 'K',
      fileExtension: 'md',
    })
    expect(getProjectResourceRoutingSpec('gates')).toMatchObject({
      indexFile: '00_INDEX.md',
      nodePrefix: 'G',
      fileExtension: 'yaml',
    })
  })

  it('解析三位编号文件并生成稳定 File ID', () => {
    expect(parseNumberedResourceFileName('rules', '010_project-rules.md')).toEqual({
      number: '010',
      slug: 'project-rules',
      fileId: 'R010',
    })
    expect(parseNumberedResourceFileName('gates', '120_validation.yaml')).toEqual({
      number: '120',
      slug: 'validation',
      fileId: 'G120',
    })
    expect(parseNumberedResourceFileName('rules', 'project-rules.md')).toBeUndefined()
    expect(parseNumberedResourceFileName('rules', '000_reserved.md')).toBeUndefined()
    expect(parseNumberedResourceFileName('gates', '010_validation.md')).toBeUndefined()
  })

  it('Node ID 使用固定三位层级且必须与所在文件编号一致', () => {
    expect(isValidResourceNodeId('rules', 'R010.010.020.010', '010')).toBe(true)
    expect(isValidResourceNodeId('architecture', 'A120.010', '120')).toBe(true)
    expect(isValidResourceNodeId('knowledge', 'K020.010.010', '020')).toBe(true)
    expect(isValidResourceNodeId('gates', 'G030.020', '030')).toBe(true)

    expect(isValidResourceNodeId('rules', 'R010.10.020', '010')).toBe(false)
    expect(isValidResourceNodeId('rules', 'R020.010', '010')).toBe(false)
    expect(isValidResourceNodeId('rules', 'A010.010', '010')).toBe(false)
  })

  it('通用 00_INDEX 校验器接受符合规范的索引', () => {
    const result = validateProjectResourceIndex(
      'rules',
      {
        interface: 'project-resource-index-v0.1',
        resource: 'rules',
        standard: 'rule-v0.1',
        files: [
          {
            id: 'R010',
            file: '010_core.md',
            title: 'Core rules',
            summary: '核心规则入口。',
            aliases: ['core'],
          },
        ],
      },
      ['00_INDEX.md', '010_core.md'],
    )

    expect(result).toEqual({ valid: true, errors: [], warnings: [] })
  })

  it('通用 00_INDEX 校验器拒绝错误 File ID、悬空和漏索引文件', () => {
    const result = validateProjectResourceIndex(
      'rules',
      {
        interface: 'project-resource-index-v0.1',
        resource: 'rules',
        standard: 'rule-v0.1',
        files: [
          {
            id: 'R020',
            file: '010_core.md',
            title: 'Core rules',
            summary: '核心规则入口。',
            aliases: ['core'],
          },
          {
            id: 'R030',
            file: '030_missing.md',
            title: 'Missing rules',
            summary: '悬空索引。',
            aliases: ['missing'],
          },
        ],
      },
      ['00_INDEX.md', '010_core.md', '020_extra.md'],
    )

    expect(result.valid).toBe(false)
    expect(result.errors).toContain('files[0].id 必须为 R010')
    expect(result.errors).toContain('Index 指向不存在文件: 030_missing.md')
    expect(result.errors).toContain('正式可路由文件未进入 00_INDEX: 020_extra.md')
  })
})
