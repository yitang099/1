#!/usr/bin/env node
/** Install deps: try npm first on Windows; pnpm elsewhere with policy overrides. */
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
process.chdir(root)

function run(cmd, args) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', cwd: root, shell: process.platform === 'win32' })
  return r.status === 0
}

const hasNuxt = existsSync(join(root, 'node_modules', 'nuxt'))

if (hasNuxt) {
  console.log('[install-deps] node_modules OK')
  process.exit(0)
}

const win = process.platform === 'win32'
if (win) {
  console.log('[install-deps] Windows: using npm install')
  if (!run('npm', ['install'])) process.exit(1)
  process.exit(0)
}

if (run('pnpm', ['install'])) process.exit(0)
console.log('[install-deps] pnpm failed, trying npm install…')
if (!run('npm', ['install'])) process.exit(1)
