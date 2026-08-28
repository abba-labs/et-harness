import { describe, expect, it } from 'vitest'
import {
  compactReviewFileSummary,
  isBuildOrTestInvocation,
  isMutationInvocation,
  isProductBuildInvocation,
} from '../src/service.js'

describe('host-independent Auto Governance action classification', () => {
  it('detects common mutating tools without treating read-only code execution as mutation', () => {
    expect(isMutationInvocation('write_file', { path: 'source/a.cpp' })).toBe(true)
    expect(isMutationInvocation('GitHub.update_file', { path: 'source/a.cpp' })).toBe(true)
    expect(isMutationInvocation('bash', { command: 'sed -i s/a/b/ source/a.cpp' })).toBe(true)
    expect(isMutationInvocation('python', {
      code: "from pathlib import Path; Path('source/a.cpp').write_text('changed')",
    })).toBe(true)
    expect(isMutationInvocation('node', {
      code: "require('fs').writeFileSync('source/a.cpp', 'changed')",
    })).toBe(true)
    expect(isMutationInvocation('python', { code: "print('read only')" })).toBe(false)
    expect(isMutationInvocation('read_file', { path: 'source/a.cpp' })).toBe(false)
  })

  it('detects formal and direct product build entry variants', () => {
    expect(isBuildOrTestInvocation('pytest', {})).toBe(true)
    expect(isBuildOrTestInvocation('bash', { command: 'cmake --build build' })).toBe(true)
    expect(isProductBuildInvocation('bash', { command: 'msbuild ET-TOOL.sln /m' })).toBe(true)
    expect(isProductBuildInvocation('bash', { command: 'devenv ET-TOOL.sln /Build Release' })).toBe(true)
    expect(isProductBuildInvocation('bash', { command: 'nmake /f Makefile' })).toBe(true)
    expect(isBuildOrTestInvocation('search', { query: 'build system' })).toBe(false)
  })

  it('keeps review handle summaries inside the Context Lint budget', () => {
    const files = Array.from({ length: 20 }, (_, index) =>
      `source/very/long/component/path/${index}/implementation_file_with_long_name.cpp`,
    )
    const summary = `${compactReviewFileSummary(files)}; decision=PENDING`
    expect(summary.length).toBeLessThanOrEqual(190)
    expect(summary).toContain('(+17 more)')
  })
})
