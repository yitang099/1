#!/usr/bin/env node
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const pkgDir = join(root, 'node_modules/ffmpeg-static')

if (!existsSync(join(pkgDir, 'package.json'))) {
  console.log('[ensure-ffmpeg] ffmpeg-static not installed, skip')
  process.exit(0)
}

const indexPath = join(pkgDir, 'index.js')
let binPath = ''
try {
  const mod = await import(indexPath)
  binPath = mod.default || mod
} catch {
  binPath = ''
}

if (binPath && existsSync(binPath)) {
  console.log('[ensure-ffmpeg] bundled ffmpeg OK')
  process.exit(0)
}

console.log('[ensure-ffmpeg] downloading ffmpeg binary (one-time)…')
const r = spawnSync(process.execPath, [join(pkgDir, 'install.js')], {
  stdio: 'inherit',
  cwd: pkgDir,
})
process.exit(r.status ?? 1)
