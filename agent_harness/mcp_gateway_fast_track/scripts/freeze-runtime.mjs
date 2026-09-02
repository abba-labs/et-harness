import { layout } from './environment-layout.mjs'
import { verifyRuntimeReleasePointer } from '../src/runtime-release.mjs'

if (process.argv.includes('--verify-only')) {
  const release = await verifyRuntimeReleasePointer(layout.activeReleasePointer)
  process.stdout.write(`${JSON.stringify({
    status: 'ACTIVE_RELEASE_VERIFIED',
    sourceSignature: release.manifest.sourceSignature,
    sourceRevision: release.manifest.sourceRevision,
    releaseRoot: release.releaseRoot,
    toolchainId: release.manifest.toolchainId ?? 'legacy-checkout-local',
  })}\n`)
  process.exit(0)
}

if (process.argv.some(argument => argument === '--force' || argument === '--activate')) {
  throw new Error(
    'freeze-runtime no longer activates or overwrites the stable Runtime. '
    + 'Use build-runtime.cmd, verify-candidate-runtime.cmd, then activate-runtime.cmd explicitly.',
  )
}

await import('./build-runtime.mjs')
