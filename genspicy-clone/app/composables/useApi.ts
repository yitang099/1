type ApiEnvelope<T> = { code: number; message: string; data: T }

export function useApi() {
  const auth = useAuth()

  async function api<T>(
    path: string,
    opts: { method?: string; query?: Record<string, string | number>; body?: unknown } = {},
  ): Promise<T> {
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
