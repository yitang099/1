import { listTemplates } from '../../utils/store'
import { ok } from '../../utils/api'

export default defineEventHandler((event) => {
  const q = getQuery(event)
  const data = listTemplates({
    page: Number(q.page || 1),
    page_size: Number(q.page_size || 20),
    q: String(q.q || ''),
    user_id: undefined,
  })
  return ok(data)
})
