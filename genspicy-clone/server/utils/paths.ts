import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

/** Resolve genspicy-clone project root even if cwd is the monorepo parent. */
export function findProjectRoot(): string {
  const candidates = [process.cwd(), join(process.cwd(), 'genspicy-clone')]
  for (const dir of candidates) {
    if (existsSync(join(dir, 'nuxt.config.ts')) && existsSync(join(dir, 'package.json'))) {
      try {
        const pkg = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8')) as { name?: string }
        if (pkg.name === 'genspicy-clone') return dir
      } catch {
        /* ignore */
      }
    }
  }
  return process.cwd()
}

export function dataDir() {
  return join(findProjectRoot(), 'server/data')
}
