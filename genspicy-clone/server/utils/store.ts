import { getCatalog, type CatalogTemplate } from './catalog'
import { mockOutputForTemplate } from './mock-output'
import { loadPersisted, savePersisted } from './persist'
import { resolveSlug } from './slug-aliases'
import type { GenerationJob, User } from './store.types'

export type Template = CatalogTemplate

type TokenRecord = { userId: string; exp: number }

const g = globalThis as typeof globalThis & {
  __cloneStore?: {
    templates: CatalogTemplate[]
    users: Map<string, User>
    tokens: Map<string, TokenRecord>
    jobs: Map<string, GenerationJob>
    favorites: Map<string, Set<string>>
    affiliate: Map<string, { signups: number; clicks: number }>
    loaded: boolean
  }
}

function persistNow() {
  const s = store()
  savePersisted({
    users: [...s.users.values()],
    tokens: [...s.tokens.entries()],
    jobs: [...s.jobs.values()],
    favorites: [...s.favorites.entries()].map(([k, v]) => [k, [...v]]),
    affiliate: Object.fromEntries(s.affiliate.entries()),
  })
}

function store() {
  if (!g.__cloneStore) {
    g.__cloneStore = {
      templates: getCatalog(),
      users: new Map(),
      tokens: new Map(),
      jobs: new Map(),
      favorites: new Map(),
      affiliate: new Map(),
      loaded: false,
    }
    const saved = loadPersisted()
    if (saved) {
      for (const u of saved.users) g.__cloneStore.users.set(u.uuid, u)
      for (const [t, r] of saved.tokens) g.__cloneStore.tokens.set(t, r)
      for (const j of saved.jobs) g.__cloneStore.jobs.set(j.id, j)
      for (const [uid, ids] of saved.favorites)
        g.__cloneStore.favorites.set(uid, new Set(ids))
      for (const [k, v] of Object.entries(saved.affiliate || {}))
        g.__cloneStore.affiliate.set(k, v)
    }
    g.__cloneStore.loaded = true
  }
  return g.__cloneStore
}

export function refreshTemplatesFromCatalog() {
  const s = store()
  s.templates = getCatalog()
}

export function listTemplates(query: {
  page?: number
  page_size?: number
  q?: string
  tag?: string
  display_scene?: string
  generate_mode?: string
  template_type?: string
  favorite_only?: boolean
  user_id?: string
  recommend?: boolean
}) {
  const s = store()
  const page = Math.max(1, Number(query.page || 1))
  const pageSize = Math.min(100, Math.max(1, Number(query.page_size || 20)))
  let items = [...s.templates].filter((t) => t.status === 'published')

  if (query.q) {
    const q = query.q.toLowerCase()
    items = items.filter(
      (t) =>
        t.template_name.toLowerCase().includes(q) ||
        t.tags.some((tag) => tag.toLowerCase().includes(q)),
    )
  }
  if (query.tag) {
    const tag = query.tag.toLowerCase()
    items = items.filter((t) => t.tags.some((x) => x.toLowerCase() === tag))
  }
  if (query.display_scene) {
    items = items.filter((t) => t.display_scene === query.display_scene)
  }
  if (query.generate_mode) {
    items = items.filter((t) => t.generate_mode === query.generate_mode)
  }
  if (query.template_type) {
    const tt = query.template_type.toLowerCase()
    items = items.filter(
      (t) =>
        t.template_type.toLowerCase() === tt ||
        t.template_type.toLowerCase().includes(tt),
    )
  }
  if (query.favorite_only && query.user_id) {
    const fav = s.favorites.get(query.user_id) || new Set()
    items = items.filter((t) => fav.has(t.id))
  }
  if (query.recommend) {
    items.sort((a, b) => (b.sort_weight || 0) - (a.sort_weight || 0))
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

export function getTemplate(idOrSlug: string) {
  const s = store()
  const slug = resolveSlug(idOrSlug)
  return (
    s.templates.find((t) => t.id === idOrSlug || t.id === slug) ||
    s.templates.find((t) => t.slug === idOrSlug || t.slug === slug)
  )
}

function randomId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`
}

function createUser(input: {
  gender: string
  email?: string
  name?: string
  role?: User['role']
  referred_by?: string
}): { user: User; access_token: string } {
  const s = store()
  const uuid = crypto.randomUUID()
  const suffix = uuid.slice(0, 8)
  const referral_code = suffix
  const user: User = {
    uuid,
    name: input.name || `User-${suffix}`,
    email: input.email || `guest-${suffix}@localhost`,
    gender: input.gender,
    role: input.role || 'guest',
    diamonds: 500,
    vip_level: 2,
    referral_code,
    referred_by: input.referred_by,
  }
  s.users.set(uuid, user)
  const token = randomId('tok')
  s.tokens.set(token, { userId: uuid, exp: Date.now() + 7 * 86400000 })
  if (input.referred_by) {
    const aff = s.affiliate.get(input.referred_by) || { signups: 0, clicks: 0 }
    aff.signups += 1
    s.affiliate.set(input.referred_by, aff)
  }
  persistNow()
  return { user, access_token: token }
}

export function guestSignUp(gender: string, referred_by?: string) {
  return createUser({ gender, referred_by })
}

export function memberSignInOrSignUp(body: {
  email?: string
  gender?: string
  name?: string
  referred_by?: string
}) {
  const gender = String(body.gender || '').trim()
  const email = String(body.email || '').trim().toLowerCase()
  if (!gender) throw createError({ statusCode: 400, message: 'invalid gender' })
  if (!email) throw createError({ statusCode: 400, message: 'invalid email' })
  const s = store()
  const existing = [...s.users.values()].find((u) => u.email === email)
  if (existing) {
    const token = randomId('tok')
    s.tokens.set(token, { userId: existing.uuid, exp: Date.now() + 7 * 86400000 })
    persistNow()
    return { user: existing, access_token: token }
  }
  return createUser({
    gender,
    email,
    name: body.name,
    role: 'member',
    referred_by: body.referred_by,
  })
}

export function resolveUser(authHeader?: string) {
  if (!authHeader?.startsWith('Bearer ')) return null
  const token = authHeader.slice(7)
  const rec = store().tokens.get(token)
  if (!rec || rec.exp < Date.now()) return null
  return store().users.get(rec.userId) || null
}

export function updateUserProfile(
  userId: string,
  patch: { name?: string; photo_url?: string },
) {
  const u = store().users.get(userId)
  if (!u) return null
  if (patch.name) u.name = patch.name
  if (patch.photo_url) u.photo_url = patch.photo_url
  persistNow()
  return u
}

export function createJob(input: {
  user: User
  template_id: string
  input_url?: string
  features?: string[]
}) {
  const tpl = getTemplate(input.template_id)
  if (!tpl) throw createError({ statusCode: 404, message: 'template not found' })
  if (tpl.vip_only && input.user.vip_level < 2) {
    throw createError({ statusCode: 403, message: 'vip required' })
  }
  let cost = tpl.base_cost
  for (const f of input.features || []) {
    const feat = tpl.features.find((x) => x.name === f)
    if (feat) cost += feat.extra_cost
  }
  if (input.user.diamonds < cost) {
    throw createError({
      statusCode: 402,
      message: `insufficient diamonds (need ${cost}, have ${input.user.diamonds})`,
    })
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
    output_url: mockOutputForTemplate(tpl.id),
    features: input.features || [],
    duration: tpl.duration,
    extend_count: 0,
    liked: false,
    created_at: now,
    updated_at: now,
  }
  store().jobs.set(id, job)
  scheduleJob(id, tpl.duration)
  persistNow()
  return job
}

function scheduleJob(id: string, baseDuration: number) {
  const extra = store().jobs.get(id)?.extend_count || 0
  const ms = 3200 + extra * 800
  const tick = (progress: number, status: GenerationJob['status']) => {
    const job = store().jobs.get(id)
    if (!job) return
    job.progress = progress
    job.status = status
    job.duration = baseDuration + extra * 8
    job.updated_at = Date.now()
    persistNow()
  }
  setTimeout(() => tick(15, 'processing'), 400)
  setTimeout(() => tick(55, 'processing'), ms * 0.35)
  setTimeout(() => tick(90, 'processing'), ms * 0.7)
  setTimeout(() => tick(100, 'completed'), ms)
}

export function extendJob(jobId: string, userId: string) {
  const job = store().jobs.get(jobId)
  if (!job || job.user_id !== userId) return null
  if (job.status !== 'completed') throw createError({ statusCode: 400, message: 'not completed' })
  const tpl = getTemplate(job.template_id)
  if (!tpl) return null
  const user = store().users.get(userId)
  if (!user) return null
  const cost = tpl.extend_cost
  if (user.diamonds < cost) throw createError({ statusCode: 402, message: 'insufficient diamonds' })
  user.diamonds -= cost
  job.extend_count += 1
  job.status = 'processing'
  job.progress = 20
  job.updated_at = Date.now()
  persistNow()
  scheduleJob(jobId, tpl.duration)
  return job
}

export function setJobLike(jobId: string, userId: string, liked: boolean) {
  const job = store().jobs.get(jobId)
  if (!job || job.user_id !== userId) return null
  job.liked = liked
  job.updated_at = Date.now()
  persistNow()
  return job
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
  persistNow()
  return true
}

export function setFavorite(userId: string, templateId: string, on: boolean) {
  const fav = store().favorites.get(userId) || new Set<string>()
  if (on) fav.add(templateId)
  else fav.delete(templateId)
  store().favorites.set(userId, fav)
  persistNow()
}

export function listFavorites(userId: string) {
  const fav = store().favorites.get(userId) || new Set<string>()
  return [...fav]
}

export function listFavoriteTemplates(userId: string, page = 1, pageSize = 20) {
  return listTemplates({
    page,
    page_size: pageSize,
    favorite_only: true,
    user_id: userId,
  })
}

export function affiliateStats(referralCode: string) {
  return store().affiliate.get(referralCode) || { signups: 0, clicks: 0 }
}

export function affiliateClick(referralCode: string) {
  const s = store()
  const aff = s.affiliate.get(referralCode) || { signups: 0, clicks: 0 }
  aff.clicks += 1
  s.affiliate.set(referralCode, aff)
  persistNow()
  return aff
}

export function grantDiamonds(userId: string, amount: number) {
  const u = store().users.get(userId)
  if (!u) return null
  u.diamonds += amount
  persistNow()
  return u
}
