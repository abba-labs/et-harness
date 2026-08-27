import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { parseKnowledgeTaxonomy } from '../src/taxonomy-parser.js'

const taxonomyPath = fileURLToPath(
  new URL('../../../global_knowledge/TAXONOMY.yaml', import.meta.url),
)

describe('Harness repository Global Knowledge', () => {
  it('仓库内 Global TAXONOMY 符合 knowledge-library-v0.2', () => {
    const taxonomy = parseKnowledgeTaxonomy(readFileSync(taxonomyPath, 'utf-8'))
    expect(taxonomy.standard).toBe('knowledge-library-v0.2')
    expect(taxonomy.roots.length).toBeGreaterThan(0)
    expect(Object.keys(taxonomy.categories).length).toBeGreaterThanOrEqual(6)
  })
})
