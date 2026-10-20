import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { dataDir } from '../../utils/paths'

const MAX_BYTES = 8 * 1024 * 1024

export default defineEventHandler(async (event) => {
  const form = await readMultipartFormData(event)
  const file = form?.find((p) => p.name === 'file' && p.filename)
  if (!file?.data?.length) {
    throw createError({ statusCode: 400, message: 'missing file' })
  }
  if (file.data.length > MAX_BYTES) {
    throw createError({ statusCode: 413, message: 'file too large (max 8MB)' })
  }
  const ext = (file.filename?.split('.').pop() || 'jpg').toLowerCase().replace(/[^a-z0-9]/g, '')
  const safeExt = ['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext) ? ext : 'jpg'
  const id = crypto.randomUUID()
  const dir = join(dataDir(), 'uploads')
  mkdirSync(dir, { recursive: true })
  const filename = `${id}.${safeExt}`
  writeFileSync(join(dir, filename), file.data)
  const url = `/media/uploads/${filename}`
  return { code: 0, message: 'ok', data: { url } }
})
