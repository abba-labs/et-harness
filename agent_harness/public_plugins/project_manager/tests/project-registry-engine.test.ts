import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { ProjectManifestV01 } from '@agent-harness/project-contract'
import { ProjectRegistryEngine } from '../src/project-registry-engine.js'

const etTool: ProjectManifestV01 = {
  contract_version: '0.1',
  project: {
    id: 'et-tool',
    name: 'ET-TOOL',
    type: 'software-hardware-tool',
    aliases: ['ettool'],
  },
  root: { markers: ['source/CMakeLists.txt'] },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {},
}

const fpga: ProjectManifestV01 = {
  contract_version: '0.1',
  project: {
    id: 'fpga-soc-validation',
    name: 'FPGA SoC Validation',
    type: 'fpga-validation',
    aliases: ['rtl-validation'],
  },
  root: { markers: ['top.xpr'] },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {
    hardware: { provider: 'fpga.vivado' },
  },
}

describe('Public Project Manager registry', () => {
  it('同一注册表同时支持不同项目类型', () => {
    const engine = new ProjectRegistryEngine()
    engine.register(etTool, '/repo/et-tool')
    engine.register(fpga, '/repo/fpga')

    expect(engine.list().map(item => item.projectId)).toEqual([
      'et-tool',
      'fpga-soc-validation',
    ])
  })

  it('项目候选匹配只提供候选，不做最终语义判断', () => {
    const engine = new ProjectRegistryEngine()
    engine.register(etTool, '/repo/et-tool')
    engine.register(fpga, '/repo/fpga')

    const result = engine.resolve('ettool')
    expect(result[0]?.projectId).toBe('et-tool')
    expect(result[0]?.matchReasons.length).toBeGreaterThan(0)
  })

  it('资源路径通过统一 kind 解析，同时暴露接口标准版本', () => {
    const engine = new ProjectRegistryEngine()
    engine.register(fpga, '/repo/fpga')

    expect(engine.getResourcePath('fpga-soc-validation', 'rules')).toBe(
      resolve('/repo/fpga', 'rules'),
    )
    expect(engine.get('fpga-soc-validation')?.resourceStandards.rules).toBe('rule-v0.1')
  })

  it('卸载项目后不再暴露 ProjectContext', () => {
    const engine = new ProjectRegistryEngine()
    const dispose = engine.register(etTool, '/repo/et-tool')
    dispose()

    expect(engine.get('et-tool')).toBeUndefined()
    expect(engine.list()).toEqual([])
  })
})
