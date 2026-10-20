export type CloneUser = {
  uuid: string
  name: string
  email: string
  gender: string
  role: 'guest' | 'member'
  diamonds: number
  vip_level: number
  photo_url?: string
  referral_code?: string
}

const TOKEN_KEY = 'genspicy-clone-token'
const REF_KEY = 'genspicy-clone-ref'

export function useAuth() {
  const token = useState<string | null>('auth-token', () => null)
  const user = useState<CloneUser | null>('auth-user', () => null)
  const ready = useState('auth-ready', () => false)

  function referredBy() {
    if (!import.meta.client) return undefined
    return localStorage.getItem(REF_KEY) || undefined
  }

  function persist(t: string | null) {
    if (import.meta.client) {
      if (t) localStorage.setItem(TOKEN_KEY, t)
      else localStorage.removeItem(TOKEN_KEY)
    }
    token.value = t
  }

  async function init() {
    if (!import.meta.client) return
    const saved = localStorage.getItem(TOKEN_KEY)
    if (saved) token.value = saved
    if (token.value) {
      try {
        const { api } = useApi()
        const data = await api<{ user: CloneUser }>('user.whoami')
        user.value = data.user
      } catch {
        persist(null)
        user.value = null
      }
    }
    ready.value = true
  }

  async function guestSignUp(gender: 'male' | 'female') {
    const { api } = useApi()
    const data = await api<{ auth: { access_token: string }; user: CloneUser }>(
      'user-guest.sign-up',
      { method: 'POST', body: { gender, referred_by: referredBy() } },
    )
    persist(data.auth.access_token)
    user.value = data.user
    return data.user
  }

  async function emailSignIn(input: { email: string; gender: 'male' | 'female'; name?: string }) {
    const { api } = useApi()
    const data = await api<{ auth: { access_token: string }; user: CloneUser }>(
      'user.sign-in-or-sign-up',
      {
        method: 'POST',
        body: { ...input, referred_by: referredBy() },
      },
    )
    persist(data.auth.access_token)
    user.value = data.user
    return data.user
  }

  function signOut() {
    persist(null)
    user.value = null
  }

  return { token, user, ready, init, guestSignUp, emailSignIn, signOut }
}

export function captureReferral(code: string) {
  if (!import.meta.client || !code) return
  localStorage.setItem(REF_KEY, code)
}
