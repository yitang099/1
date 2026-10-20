#!/usr/bin/env node
/**
 * One command: install deps, download ffmpeg, build, start, open browser.
 * Windows: double-click start-windows.bat instead if you prefer.
 */
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
process.chdir(root)

const port = process.env.PORT || '3000'
const host = process.env.HOST || '127.0.0.1'

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', cwd: root, shell: false, ...opts })
  if (r.status !== 0) process.exit(r.status ?? 1)
}

function which(cmd) {
  const r = spawnSync(process.platform === 'win32' ? 'where' : 'which', [cmd], {
    encoding: 'utf8',
    shell: true,
  })
  return r.status === 0
}

if (!which('node')) {
  console.error('请先安装 Node.js 20+：https://nodejs.org/')
  process.exit(1)
}

if (!which('pnpm')) {
  console.log('[local] 启用 pnpm…')
  run('corepack', ['enable'], { shell: true })
  if (!which('pnpm')) run('npm', ['install', '-g', 'pnpm'], { shell: true })
}

console.log('[local] pnpm install …')
run('pnpm', ['install'])

const serverEntry = join(root, '.output/server/index.mjs')
if (!existsSync(serverEntry)) {
  console.log('[local] pnpm build …（首次约 1 分钟）')
  run('pnpm', ['build'])
}

async function waitHealth(maxSec = 90) {
  const url = `http://${host === '0.0.0.0' ? '127.0.0.1' : host}:${port}/api/health`
  for (let i = 0; i < maxSec; i++) {
    try {
      const res = await fetch(url)
      if (res.ok) return true
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  return false
}

function openBrowser(url) {
  const plat = process.platform
  if (plat === 'win32') spawn('cmd', ['/c', 'start', '', url], { detached: true, stdio: 'ignore' })
  else if (plat === 'darwin') spawn('open', [url], { detached: true, stdio: 'ignore' })
  else spawn('xdg-open', [url], { detached: true, stdio: 'ignore' })
}

console.log(`[local] 启动 http://127.0.0.1:${port}/ …`)
const child = spawn(process.execPath, [serverEntry], {
  stdio: 'inherit',
  env: {
    ...process.env,
    PORT: port,
    HOST: '0.0.0.0',
    NITRO_HOST: '0.0.0.0',
    NITRO_PORT: port,
    NUXT_PUBLIC_SITE_URL: `http://127.0.0.1:${port}`,
  },
})

void (async () => {
  const ok = await waitHealth()
  if (ok) {
    const openUrl = `http://127.0.0.1:${port}/`
    console.log(`[local] 就绪，打开浏览器: ${openUrl}`)
    openBrowser(openUrl)
  } else {
    console.warn('[local] 健康检查超时，请手动打开 http://127.0.0.1:' + port)
  }
})()

child.on('exit', (code) => process.exit(code ?? 0))
