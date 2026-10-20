import { readFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'
import { dataDir } from '../../../utils/paths'

export default defineEventHandler((event) => {
  const name = String(getRouterParam(event, 'name') || '')
  if (!/^[a-f0-9-]+\.(jpg|jpeg|png|webp|gif)$/i.test(name)) {
    throw createError({ statusCode: 400, message: 'invalid name' })
  }
  const path = join(dataDir(), 'uploads', name)
  if (!existsSync(path)) throw createError({ statusCode: 404, message: 'not found' })
  const buf = readFileSync(path)
  const ext = name.split('.').pop()?.toLowerCase()
  const type =
    ext === 'png'
      ? 'image/png'
      : ext === 'webp'
        ? 'image/webp'
        : ext === 'gif'
          ? 'image/gif'
          : 'image/jpeg'
  setHeader(event, 'Content-Type', type)
  setHeader(event, 'Cache-Control', 'public, max-age=86400')
  return buf
})
