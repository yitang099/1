import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { dataDir } from './paths'
import type { GenerationJob, User } from './store.types'

type Persisted = {
  users: User[]
  tokens: [string, { userId: string; exp: number }][]
  jobs: GenerationJob[]
  favorites: [string, string[]][]
  affiliate: Record<string, { signups: number; clicks: number }>
}

const path = () => join(dataDir(), 'runtime-store.json')

export function loadPersisted(): Persisted | null {
  const p = path()
  if (!existsSync(p)) return null
  try {
    return JSON.parse(readFileSync(p, 'utf8')) as Persisted
  } catch {
    return null
  }
}

export function savePersisted(data: Persisted) {
  const dir = dataDir()
  mkdirSync(dir, { recursive: true })
  writeFileSync(path(), JSON.stringify(data, null, 0))
}
