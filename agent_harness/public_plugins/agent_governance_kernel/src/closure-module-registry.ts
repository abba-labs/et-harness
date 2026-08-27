import {
  MANDATORY_CLOSURE_MODULE_IDS,
  type ClosureModule,
  type MandatoryClosureModuleId,
} from './contracts.js'
import { assertKernelIdentifier } from './lifecycle.js'

const mandatoryOrder = new Map<string, number>(
  MANDATORY_CLOSURE_MODULE_IDS.map((id, index) => [id, index]),
)

const mandatorySet = new Set<string>(MANDATORY_CLOSURE_MODULE_IDS)

export class ClosureModuleRegistry {
  private readonly modules = new Map<string, ClosureModule>()

  register(module: ClosureModule): () => void {
    assertKernelIdentifier('closure module id', module.id)
    assertKernelIdentifier('closure module version', module.version)
    if (this.modules.has(module.id)) throw new Error(`Closure Module already registered: ${module.id}`)
    if (!Array.isArray(module.domains) || module.domains.length === 0) {
      throw new Error(`Closure Module ${module.id} must declare at least one domain`)
    }
    if (mandatorySet.has(module.id) && !module.mandatory) {
      throw new Error(`Mandatory Closure Module ${module.id} cannot be registered as optional`)
    }
    if (module.mandatory && !mandatorySet.has(module.id)) {
      throw new Error(`Closure Module ${module.id} cannot extend the fixed Kernel mandatory set`)
    }
    this.modules.set(module.id, module)
    return () => { this.modules.delete(module.id) }
  }

  get(moduleId: string): ClosureModule | undefined {
    return this.modules.get(moduleId)
  }

  list(): readonly ClosureModule[] {
    return [...this.modules.values()].sort((left, right) => {
      const leftRank = mandatoryOrder.get(left.id)
      const rightRank = mandatoryOrder.get(right.id)
      if (leftRank !== undefined || rightRank !== undefined) {
        if (leftRank === undefined) return 1
        if (rightRank === undefined) return -1
        return leftRank - rightRank
      }
      return left.id.localeCompare(right.id)
    })
  }

  listMandatory(): readonly ClosureModule[] {
    return MANDATORY_CLOSURE_MODULE_IDS
      .map(id => this.modules.get(id))
      .filter((module): module is ClosureModule => module !== undefined)
  }

  missingMandatory(): readonly MandatoryClosureModuleId[] {
    return MANDATORY_CLOSURE_MODULE_IDS.filter(id => !this.modules.has(id))
  }
}
