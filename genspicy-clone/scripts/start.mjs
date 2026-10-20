#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
process.chdir(root)

const port = process.env.PORT || '3000'
const host = process.env.HOST || '0.0.0.0'
const server = join(root, '.output/server/index.mjs')

if (!existsSync(server)) {
  console.error('[genspicy-clone] Missing build. Run: pnpm build && pnpm start')
  process.exit(1)
}

console.log(`[genspicy-clone] Production server http://localhost:${port}/`)

const child = spawn(process.execPath, [server], {
  stdio: 'inherit',
  env: {
    ...process.env,
    PORT: port,
    HOST: host,
    NITRO_HOST: host,
    NITRO_PORT: port,
  },
})

child.on('exit', (code) => process.exit(code ?? 0))
