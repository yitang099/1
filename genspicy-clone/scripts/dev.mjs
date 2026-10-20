#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
process.chdir(root)

const port = process.env.PORT || '3000'
const host = process.env.HOST || '0.0.0.0'

const catalog = join(root, 'server/data/templates.catalog.json')
const sample = join(root, 'server/data/templates.catalog.sample.json')
if (!existsSync(catalog) && !existsSync(sample)) {
  console.warn(
    '[genspicy-clone] No template catalog found. Run: pnpm import:templates\n' +
      '  (Using 4 seed templates until then.)',
  )
}

console.log(`[genspicy-clone] Starting dev server at http://localhost:${port}/`)
console.log(`[genspicy-clone] Health check: http://localhost:${port}/api/health`)

const child = spawn('npx', ['nuxt', 'dev', '--host', host, '--port', port], {
  stdio: 'inherit',
  shell: false,
  env: { ...process.env, NUXT_TELEMETRY_DISABLED: '1' },
})

child.on('exit', (code) => process.exit(code ?? 0))
