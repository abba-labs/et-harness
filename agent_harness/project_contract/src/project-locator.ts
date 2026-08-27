import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

export function isProjectRoot(candidate: string, markers: readonly string[]): boolean {
  const root = resolve(candidate)
  return markers.every(marker => existsSync(resolve(root, marker)))
}

export function findProjectRoot(
  markers: readonly string[],
  startPath: string = process.cwd(),
): string {
  if (markers.length === 0) {
    throw new Error('Project Contract 要求至少一个 root marker')
  }

  let current = resolve(startPath)
  for (;;) {
    if (isProjectRoot(current, markers)) return current
    const parent = dirname(current)
    if (parent === current) break
    current = parent
  }

  throw new Error(`无法从 ${resolve(startPath)} 向上发现满足 Project Contract 的项目根目录`)
}
