import type { CloneUser } from './useAuth'

export type GenerationJob = {
  id: string
  template_name: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  output_url?: string
  input_url?: string
  liked?: boolean
  extend_count?: number
  duration?: number
  created_at: number
}

export function useGeneration() {
  const { api } = useApi()
  const auth = useAuth()
  const live = useGenspicyLive()

  async function refreshUser() {
    if (live.isActive.value) {
      await live.verify()
      return
    }
    const whoami = await api<{ user: CloneUser }>('user.whoami')
    auth.user.value = whoami.user
  }

  async function create(templateId: string, inputUrl: string, features: string[]) {
    const body = live.isActive.value
      ? {
          template_id: templateId,
          input_medias: [{ type: 'image', url: inputUrl }],
          selected_features: features,
        }
      : {
          template_id: templateId,
          input_url: inputUrl,
          features,
        }

    const data = await api<{ item: GenerationJob }>('user-generation-content.create', {
      method: 'POST',
      body,
    })
    await refreshUser()
    return data.item
  }

  async function poll(id: string, onTick: (job: GenerationJob) => void) {
    const max = live.isActive.value ? 120 : 40
    const interval = live.isActive.value ? 2000 : 500
    for (let i = 0; i < max; i++) {
      const data = await api<{ item: GenerationJob }>('user-generation-content.get', {
        query: { id },
      })
      onTick(data.item)
      if (data.item.status === 'completed' || data.item.status === 'failed') return data.item
      await new Promise((r) => setTimeout(r, interval))
    }
    throw new Error('Generation timed out')
  }

  async function extend(id: string) {
    const data = await api<{ item: GenerationJob }>('user-generation-content.extend', {
      method: 'POST',
      body: { id },
    })
    return data.item
  }

  async function setLike(id: string, liked: boolean) {
    const data = await api<{ item: GenerationJob }>('user-generation-content.like-status.update', {
      method: 'POST',
      body: { id, liked },
    })
    return data.item
  }

  return { create, poll, extend, setLike }
}
