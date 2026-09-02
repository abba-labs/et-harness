import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { tmpdir } from 'node:os'

import { verifyLockfileInstallation } from '../scripts/toolchain.mjs'

const root = await mkdtemp(join(tmpdir(), 'et-toolchain-lock-'))
after(async () => rm(root, { recursive: true, force: true }))

const writeJson = (path, value) => writeFile(path, `${JSON.stringify(value)}\n`, 'utf8')

const setup = async (name, installedVersion = '1.0.0') => {
  const directory = resolve(root, name)
  await mkdir(resolve(directory, 'node_modules', 'required-package'), { recursive: true })
  await writeJson(resolve(directory, 'package-lock.json'), {
    lockfileVersion: 3,
    packages: {
      '': { name: 'fixture' },
      'node_modules/required-package': { version: '1.0.0' },
      'node_modules/platform-optional': { version: '2.0.0', optional: true },
    },
  })
  await writeJson(
    resolve(directory, 'node_modules', 'required-package', 'package.json'),
    { name: 'required-package', version: installedVersion },
  )
  return directory
}

test('full lock verification requires non-optional packages and permits absent optional packages', async () => {
  const directory = await setup('valid')
  const result = verifyLockfileInstallation(directory)
  assert.equal(result.verifiedPackageCount, 1)
  assert.equal(result.skippedOptionalCount, 1)
})

test('full lock verification rejects an installed version that differs from the lockfile', async () => {
  const directory = await setup('mismatch', '9.9.9')
  assert.throws(
    () => verifyLockfileInstallation(directory),
    /Shared Toolchain lockfile mismatch/,
  )
})
