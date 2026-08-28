import { describe, expect, it } from 'vitest'
import { normalizeInlineContextItems } from '../src/context-management-service.js'

describe('dynamic Inline Context Items', () => {
  it('normalizes valid provider-contributed items deterministically', () => {
    expect(normalizeInlineContextItems([{
      id: 'contribution:synthetic:scope',
      title: 'Synthetic Scope',
      content: 'write_scope:\n  allowed:\n  - docs/**',
      priority: 'required',
      provenance: 'provider://synthetic/context',
    }])).toEqual([{
      id: 'contribution:synthetic:scope',
      title: 'Synthetic Scope',
      content: 'write_scope:\n  allowed:\n  - docs/**',
      priority: 'required',
      provenance: 'provider://synthetic/context',
    }])
  })

  it('rejects duplicate and Runtime-reserved IDs', () => {
    const item = {
      id: 'contribution:synthetic:scope',
      title: 'Synthetic Scope',
      content: 'scope',
      provenance: 'provider://synthetic/context',
    } as const
    expect(() => normalizeInlineContextItems([item, item])).toThrow(/重复/)
    expect(() => normalizeInlineContextItems([{
      ...item,
      id: 'task-ledger',
    }])).toThrow(/保留项冲突/)
  })

  it('rejects excessive contribution content', () => {
    expect(() => normalizeInlineContextItems([{
      id: 'contribution:synthetic:large',
      title: 'Large',
      content: 'x'.repeat(8_001),
      provenance: 'provider://synthetic/context',
    }])).toThrow(/字符上限/)
  })
})
