import { listTemplates } from '../../utils/store'
import { ok } from '../../utils/api'

export default defineEventHandler((event) => {
  const q = getQuery(event)
  const data = listTemplates({
    page: Number(q.page || 1),
    page_size: Number(q.page_size || 24),
    q: String(q.q || ''),
    recommend: true,
    user_id: undefined,
  })
  return ok(data)
})
