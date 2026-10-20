type ApiEnvelope<T> = { code: number; message: string; data: T }

/** RPC paths that must hit official Genspicy when live token is connected. */
const LIVE_GENERATION_RPC = new Set([
  'user.whoami',
  'user-generation-content.create',
  'user-generation-content.get',
  'user-generation-content.list',
  'user-generation-content.extend',
  'user-generation-content.delete',
  'user-generation-content.like-status.update',
])

export function useApi() {
  const auth = useAuth()
  const live = useGenspicyLive()

  async function api<T>(
    path: string,
    opts: { method?: string; query?: Record<string, string | number>; body?: unknown } = {},
  ): Promise<T> {
    if (live.isActive.value && LIVE_GENERATION_RPC.has(path)) {
      return live.rpc<T>(path, opts)
    }

    const headers: Record<string, string> = {}
    if (auth.token.value) headers.Authorization = `Bearer ${auth.token.value}`
    const res = await $fetch<ApiEnvelope<T>>(`/api/v1/${path}`, {
      method: (opts.method || 'GET') as 'GET' | 'POST',
      query: opts.query,
      body: opts.body,
      headers,
    })
    if (res.code !== 0) {
      throw new Error(res.message || `API error ${res.code}`)
    }
    return res.data
  }

  async function homeTemplates(page = 1, pageSize = 24) {
    const res = await $fetch<ApiEnvelope<{ items: unknown[]; total: number }>>(
      '/api/home/cached-generation-template-list',
      { query: { page, page_size: pageSize } },
    )
    if (res.code !== 0) throw new Error(res.message)
    return res.data
  }

  return { api, homeTemplates }
}
