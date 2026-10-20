import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { GenerationJob, User } from './store.types'

type Persisted = {
  users: User[]
  tokens: [string, { userId: string; exp: number }][]
  jobs: GenerationJob[]
  favorites: [string, string[]][]
  affiliate: Record<string, { signups: number; clicks: number }>
}

const path = join(process.cwd(), 'server/data/runtime-store.json')

export function loadPersisted(): Persisted | null {
  if (!existsSync(path)) return null
  try {
    return JSON.parse(readFileSync(path, 'utf8')) as Persisted
  } catch {
    return null
  }
}

export function savePersisted(data: Persisted) {
  mkdirSync(join(process.cwd(), 'server/data'), { recursive: true })
  writeFileSync(path, JSON.stringify(data, null, 0))
}
