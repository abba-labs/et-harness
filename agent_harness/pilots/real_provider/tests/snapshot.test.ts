import { describe, expect, it } from 'vitest'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { createEtToolProjectSnapshot } from '../src/et-tool-snapshot.js'

const makeSourceRoot = (): string => {
  const root = mkdtempSync(join(tmpdir(), 'level2c-source-'))
  mkdirSync(join(root, 'source', 'apps'), { recursive: true })
  writeFileSync(join(root, 'source', 'CMakeLists.txt'), '# marker\n', 'utf8')
  const project = join(root, 'agent_harness', 'projects', 'et_tool')
  for (const resource of ['architecture', 'rules', 'knowledge', 'gates']) {
    mkdirSync(join(project, resource), { recursive: true })
    writeFileSync(join(project, resource, '00_INDEX.md'), `${resource}-source\n`, 'utf8')
  }
  writeFileSync(join(project, 'project.yaml'), 'contract_version: "0.1"\n', 'utf8')
  mkdirSync(join(project, 'node_modules'), { recursive: true })
  writeFileSync(join(project, 'node_modules', 'must-not-copy.txt'), 'noise\n', 'utf8')
  return root
}

describe('Level 2C ET-TOOL project snapshot', () => {
  it('copies only governed project resources and isolates mutations from the source tree', () => {
    const source = makeSourceRoot()
    const snapshot = createEtToolProjectSnapshot(source)
    try {
      expect(existsSync(join(snapshot.root, 'agent_harness', 'projects', 'et_tool', 'project.yaml'))).toBe(true)
      expect(existsSync(join(snapshot.root, 'source', 'CMakeLists.txt'))).toBe(true)
      expect(existsSync(join(snapshot.root, 'source', 'apps'))).toBe(true)
      expect(existsSync(join(snapshot.root, 'agent_harness', 'projects', 'et_tool', 'node_modules'))).toBe(false)

      const snapshotKnowledge = join(
        snapshot.root,
        'agent_harness',
        'projects',
        'et_tool',
        'knowledge',
        '00_INDEX.md',
      )
      writeFileSync(snapshotKnowledge, 'snapshot-mutated\n', 'utf8')
      const sourceKnowledge = join(
        source,
        'agent_harness',
        'projects',
        'et_tool',
        'knowledge',
        '00_INDEX.md',
      )
      expect(readFileSync(sourceKnowledge, 'utf8')).toBe('knowledge-source\n')
    } finally {
      snapshot.dispose()
      rmSync(source, { recursive: true, force: true })
    }
  })
})
