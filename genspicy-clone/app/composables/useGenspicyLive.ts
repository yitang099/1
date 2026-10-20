const LIVE_TOKEN_KEY = 'genspicy-live-access-token'

type ApiEnvelope<T> = { code: number; message: string; data: T }

export function useGenspicyLive() {
  const config = useRuntimeConfig()
  const token = useState<string | null>('genspicy-live-token', () => null)
  const whoami = useState<Record<string, unknown> | null>('genspicy-live-whoami', () => null)
  const lastError = useState<string | null>('genspicy-live-error', () => null)

  const apiBase = computed(() => String(config.public.genspicyApiBase || 'https://api.genspicy.ai'))

  function loadTokenFromStorage() {
    if (!import.meta.client) return
    token.value = localStorage.getItem(LIVE_TOKEN_KEY)
  }

  function setToken(t: string | null) {
    if (import.meta.client) {
      if (t) localStorage.setItem(LIVE_TOKEN_KEY, t)
      else localStorage.removeItem(LIVE_TOKEN_KEY)
    }
    token.value = t
    whoami.value = null
    lastError.value = null
  }

  const isActive = computed(() => Boolean(token.value?.trim()))

  async function rpc<T>(
    path: string,
    opts: { method?: string; query?: Record<string, string | number>; body?: unknown } = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
    }
    if (token.value) headers.Authorization = `Bearer ${token.value.trim()}`
    const url = `${apiBase.value}/api/v1/${path}`
    const res = await $fetch<ApiEnvelope<T>>(url, {
      method: (opts.method || 'GET') as 'GET' | 'POST',
      query: opts.query,
      body: opts.body,
      headers,
    })
    if (res.code !== 0) {
      throw new Error(res.message || `upstream ${res.code}`)
    }
    return res.data
  }

  async function verify() {
    lastError.value = null
    try {
      const data = await rpc<{ user: Record<string, unknown> }>('user.whoami')
      whoami.value = data.user
      return data.user
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : 'verify failed'
      whoami.value = null
      throw e
    }
  }

  function disconnect() {
    setToken(null)
  }

  return {
    token,
    whoami,
    lastError,
    isActive,
    loadTokenFromStorage,
    setToken,
    verify,
    disconnect,
    rpc,
  }
}
