export type User = {
  uuid: string
  name: string
  email: string
  gender: string
  role: 'guest' | 'member'
  diamonds: number
  vip_level: number
  photo_url?: string
  referral_code?: string
  referred_by?: string
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
  duration: number
  extend_count: number
  liked: boolean
  created_at: number
  updated_at: number
  /** @internal mock scheduler handles */
  _timerIds?: ReturnType<typeof setTimeout>[]
}
