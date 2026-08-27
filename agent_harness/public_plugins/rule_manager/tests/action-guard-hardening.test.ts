import { describe, expect, it } from 'vitest'
import type { RuleNode } from '../src/contracts.js'
import { evaluateRuleActionGuards } from '../src/action-guard.js'

const guardNode = {
  id: 'R900.300.020',
  directContent: `Level: MUST
Enforcement: ACTION_GUARD
Action: PRODUCT_BUILD
Allow: [source/release/release_gui.bat]
Deny: [cmake, ninja, ctest, make, nmake, msbuild, devenv, meson]`,
  isLeaf: true,
} as RuleNode

const evaluate = (command: string) => evaluateRuleActionGuards([guardNode], {
  actionKind: 'PRODUCT_BUILD',
  actionText: JSON.stringify({ command }),
})

describe('R900 canonical Release entry guard', () => {
  it('allows canonical slash, Windows separator and explicit relative forms', () => {
    expect(evaluate('source/release/release_gui.bat --mode dev').allowed).toBe(true)
    expect(evaluate('source\\release\\release_gui.bat --mode dev').allowed).toBe(true)
    expect(evaluate('.\\source\\release\\release_gui.bat --mode dev').allowed).toBe(true)
  })

  it('rejects suffix, traversal, prefix and direct build entry variants', () => {
    expect(evaluate('source/release/release_gui.bat.exe --mode dev').allowed).toBe(false)
    expect(evaluate('../evil/source/release/release_gui.bat --mode dev').allowed).toBe(false)
    expect(evaluate('tools/source/release/release_gui.bat --mode dev').allowed).toBe(false)
    expect(evaluate('msbuild ET-TOOL.sln /m').allowed).toBe(false)
    expect(evaluate('devenv ET-TOOL.sln /Build Release').allowed).toBe(false)
    expect(evaluate('nmake /f Makefile').allowed).toBe(false)
  })
})
