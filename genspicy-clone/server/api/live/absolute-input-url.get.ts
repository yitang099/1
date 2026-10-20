import { readAuth } from '../../utils/api'

/** Turn site-relative upload path into absolute URL for official API input_medias */
export default defineEventHandler((event) => {
  const q = getQuery(event)
  const path = String(q.path || '')
  if (!path.startsWith('/media/uploads/')) {
    throw createError({ statusCode: 400, message: 'path must be /media/uploads/...' })
  }
  const host = getRequestHeader(event, 'x-forwarded-host') || getRequestHeader(event, 'host')
  const proto = getRequestHeader(event, 'x-forwarded-proto') || 'http'
  if (!host) throw createError({ statusCode: 400, message: 'missing host' })
  readAuth(event) // optional: could require auth later
  return {
    code: 0,
    message: 'ok',
    data: { url: `${proto}://${host}${path}` },
  }
})
