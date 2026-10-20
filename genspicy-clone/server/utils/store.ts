import seedTemplates from '../data/templates.seed.json'

export type Template = (typeof seedTemplates)[number] & {
  status: 'published'
}

export type User = {
  uuid: string
  name: string
  email: string
  gender: string
  role: 'guest' | 'member'
  diamonds: number
  vip_level: number
}

export type GenerationJob = {
  id: string
  user_id: string
  template_id: string
  template_name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  input_url?: string
  output_url?: string
  features: string[]
  created_at: number
  updated_at: number
}

type TokenRecord = { userId: string; exp: number }

const g = globalThis as typeof globalThis & {
  __cloneStore?: {
    templates: Template[]
    users: Map<string, User>
    tokens: Map<string, TokenRecord>
    jobs: Map<string, GenerationJob>
    favorites: Map<string, Set<string>>
  }
}

function store() {
  if (!g.__cloneStore) {
    g.__cloneStore = {
      templates: seedTemplates.map((t) => ({ ...t, status: 'published' as const })),
      users: new Map(),
      tokens: new Map(),
      jobs: new Map(),
      favorites: new Map(),
    }
  }
  return g.__cloneStore
}

export function listTemplates(query: {
  page?: number
  page_size?: number
  q?: string
  favorite_only?: boolean
  user_id?: string
}) {
  const s = store()
  const page = Math.max(1, Number(query.page || 1))
  const pageSize = Math.min(100, Math.max(1, Number(query.page_size || 20)))
  let items = [...s.templates]
  if (query.q) {
    const q = query.q.toLowerCase()
    items = items.filter(
      (t) =>
        t.template_name.toLowerCase().includes(q) ||
        t.tags.some((tag) => tag.toLowerCase().includes(q)),
    )
  }
  if (query.favorite_only && query.user_id) {
    const fav = s.favorites.get(query.user_id) || new Set()
    items = items.filter((t) => fav.has(t.id))
  }
  const total = items.length
  const start = (page - 1) * pageSize
  const slice = items.slice(start, start + pageSize).map((t) => ({
    ...t,
    is_favorited: query.user_id
      ? (s.favorites.get(query.user_id)?.has(t.id) ?? false)
      : false,
  }))
  return { items: slice, total, page, page_size: pageSize }
}

export function getTemplate(id: string) {
  return store().templates.find((t) => t.id === id)
}

function randomId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`
}

export function guestSignUp(gender: string): { user: User; access_token: string } {
  const s = store()
  const uuid = crypto.randomUUID()
  const suffix = uuid.slice(0, 8)
  const user: User = {
    uuid,
    name: `User-${suffix}`,
    email: `guest-${suffix}@localhost`,
    gender,
    role: 'guest',
    diamonds: 500,
    vip_level: 2,
  }
  s.users.set(uuid, user)
  const token = randomId('tok')
  s.tokens.set(token, { userId: uuid, exp: Date.now() + 7 * 86400000 })
  return { user, access_token: token }
}

export function resolveUser(authHeader?: string) {
  if (!authHeader?.startsWith('Bearer ')) return null
  const token = authHeader.slice(7)
  const rec = store().tokens.get(token)
  if (!rec || rec.exp < Date.now()) return null
  return store().users.get(rec.userId) || null
}

export function createJob(input: {
  user: User
  template_id: string
  input_url?: string
  features?: string[]
}) {
  const tpl = getTemplate(input.template_id)
  if (!tpl) throw createError({ statusCode: 404, message: 'template not found' })
  let cost = tpl.base_cost
  for (const f of input.features || []) {
    const feat = tpl.features.find((x) => x.name === f)
    if (feat) cost += feat.extra_cost
  }
  if (input.user.diamonds < cost) {
    throw createError({ statusCode: 402, message: 'insufficient diamonds' })
  }
  input.user.diamonds -= cost
  const id = crypto.randomUUID()
  const now = Date.now()
  const job: GenerationJob = {
    id,
    user_id: input.user.uuid,
    template_id: tpl.id,
    template_name: tpl.template_name,
    status: 'pending',
    progress: 0,
    input_url: input.input_url,
    output_url: tpl.output_media,
    features: input.features || [],
    created_at: now,
    updated_at: now,
  }
  store().jobs.set(id, job)
  scheduleJob(id)
  return job
}

function scheduleJob(id: string) {
  const tick = (progress: number, status: GenerationJob['status']) => {
    const job = store().jobs.get(id)
    if (!job) return
    job.progress = progress
    job.status = status
    job.updated_at = Date.now()
  }
  setTimeout(() => tick(15, 'processing'), 400)
  setTimeout(() => tick(55, 'processing'), 1200)
  setTimeout(() => tick(90, 'processing'), 2200)
  setTimeout(() => tick(100, 'completed'), 3200)
}

export function getJob(id: string, userId?: string) {
  const job = store().jobs.get(id)
  if (!job) return null
  if (userId && job.user_id !== userId) return null
  return job
}

export function listJobs(userId: string, page = 1, pageSize = 20) {
  const jobs = [...store().jobs.values()]
    .filter((j) => j.user_id === userId)
    .sort((a, b) => b.created_at - a.created_at)
  const start = (page - 1) * pageSize
  return {
    items: jobs.slice(start, start + pageSize),
    total: jobs.length,
    page,
    page_size: pageSize,
  }
}

export function deleteJob(id: string, userId: string) {
  const job = store().jobs.get(id)
  if (!job || job.user_id !== userId) return false
  store().jobs.delete(id)
  return true
}

export function setFavorite(userId: string, templateId: string, on: boolean) {
  const fav = store().favorites.get(userId) || new Set<string>()
  if (on) fav.add(templateId)
  else fav.delete(templateId)
  store().favorites.set(userId, fav)
}

export function listFavorites(userId: string) {
  const fav = store().favorites.get(userId) || new Set<string>()
  return [...fav]
}
