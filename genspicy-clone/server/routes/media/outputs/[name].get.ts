import { readFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'
import { dataDir } from '../../../utils/paths'

export default defineEventHandler((event) => {
  const name = String(getRouterParam(event, 'name') || '')
  if (!/^[a-f0-9-]+\.mp4$/i.test(name)) {
    throw createError({ statusCode: 400, message: 'invalid name' })
  }
  const path = join(dataDir(), 'outputs', name)
  if (!existsSync(path)) throw createError({ statusCode: 404, message: 'not found' })
  setHeader(event, 'Content-Type', 'video/mp4')
  setHeader(event, 'Cache-Control', 'public, max-age=86400')
  return readFileSync(path)
})
