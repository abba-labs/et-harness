import { register } from 'node:module'

register(new URL('./toolchain-loader.mjs', import.meta.url), import.meta.url)
