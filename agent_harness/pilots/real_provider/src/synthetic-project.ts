import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { tmpdir } from 'node:os'
import type { ProjectManifestV01 } from '@agent-harness/project-contract'

export interface SyntheticProjectFixture {
  readonly root: string
  readonly manifest: ProjectManifestV01
  dispose(): void
}

const write = (root: string, relative: string, content: string): void => {
  const file = join(root, relative)
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, content, 'utf8')
}

export function createSyntheticProjectFixture(): SyntheticProjectFixture {
  const root = mkdtempSync(join(tmpdir(), 'agent-harness-level2c-'))
  mkdirSync(join(root, 'architecture'), { recursive: true })
  mkdirSync(join(root, 'rules'), { recursive: true })
  mkdirSync(join(root, 'knowledge'), { recursive: true })
  mkdirSync(join(root, 'gates'), { recursive: true })
  writeFileSync(join(root, 'project.marker'), 'synthetic\n', 'utf8')

  write(root, 'architecture/00_INDEX.md', `---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_release.md
    title: Delivery Architecture
    summary: Release and verification architecture
    aliases: [release, build, validation, evidence, gate]
---
`)
  write(root, 'architecture/010_release.md', `# [A010] Delivery Architecture
Role: governed delivery flow

## [A010.010] Governed Delivery Pipeline
Role: Code Gate precedes Release build and validation evidence.
Boundary: build execution is not a Code Gate responsibility.
Relations: R010.010, G010.010
`)

  write(root, 'rules/00_INDEX.md', `---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_release.md
    title: Delivery Rules
    summary: Release build and evidence rules
    aliases: [release, build, gate, evidence, validation]
---
`)
  write(root, 'rules/010_release.md', `# [R010] Delivery Rules

## [R010.010] Build After Gate
Level: MUST
When: 代码修改后准备正式构建
Rule: 必须先完成适用 Code Gate，再通过正式 Release 入口构建，随后执行所需验证并记录 Evidence。
Refs: [A010.010, G010.010]
`)

  write(root, 'knowledge/TAXONOMY.yaml', `standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Delivery Flow
    summary: Project-specific delivery and validation knowledge.
`)
  write(root, 'knowledge/001_library.md', `# [K001] Delivery Flow

## [K001.001] Gate Build Evidence Sequence
Status: VALIDATED
Category: C010
Fact: The governed sequence is Code Gate -> Release Build -> Validation -> Evidence.
Provenance: SYNTHETIC-BASELINE
Tags: [gate, release, validation, evidence]
Refs: [A010.010, R010.010, G010.010]
`)

  write(root, 'gates/00_INDEX.md', `---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_delivery.yaml
    title: Delivery Gate
    summary: Review before formal Release build
    aliases: [gate, release, build, validation, evidence]
---
`)
  write(root, 'gates/010_delivery.yaml', `standard: gate-v0.1
file_id: G010
title: Delivery Gate
nodes:
  - id: G010.010
    title: Pre-Build Review
    gate:
      level: MUST
      when: 代码修改后准备正式构建
      steps:
        - id: review
          tool: code.review
      pass:
        mode: all_steps_pass
      refs: [R010.010]
`)

  const manifest: ProjectManifestV01 = {
    contract_version: '0.1',
    project: {
      id: 'synthetic-level2c',
      name: 'Synthetic Level 2C Project',
      type: 'test',
      aliases: ['synthetic-level2c'],
    },
    root: { markers: ['project.marker'] },
    resources: {
      architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
      rules: { path: 'rules/', standard: 'rule-v0.1' },
      knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
      gates: { path: 'gates/', standard: 'gate-v0.1' },
    },
    adapters: {},
  }

  return {
    root,
    manifest,
    dispose: () => rmSync(root, { recursive: true, force: true }),
  }
}
