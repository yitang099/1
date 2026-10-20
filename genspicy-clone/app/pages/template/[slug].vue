<template>
  <div v-if="pending" class="state">Loading…</div>
  <div v-else-if="!tpl" class="state">Template not found</div>
  <div v-else class="detail">
    <div class="preview card">
      <img :src="tpl.cover_url" :alt="tpl.template_name" />
    </div>
    <div class="panel">
      <h1>{{ tpl.template_name }}</h1>
      <div class="row">
        <span v-for="tag in tpl.tags" :key="tag" class="tag">{{ tag }}</span>
      </div>
      <p v-if="live.isActive.value" class="notice live">
        已连接<strong>官方 API</strong>：Generate 将走真实推理队列（需官网会员 Token，消耗真实钻石）。
      </p>
      <p v-else class="notice">
        当前为<strong>Mock 演示</strong>。要与线上一致的真实生成，请先在
        <NuxtLink to="/user/live-account">真实生成</NuxtLink>
        页连接官网 Token。
      </p>
      <p class="meta">
        {{ tpl.generate_mode }} · {{ tpl.duration }}s · 💎 {{ totalCost }} (base {{ tpl.base_cost }})
        <span v-if="auth.user.value && auth.user.value.diamonds < totalCost" class="warn">
          钻石不足，请到 Profile 领取演示钻石或换更便宜的模板
        </span>
      </p>

      <label class="field">
        <span>输入图片（上传或 HTTPS 链接）</span>
        <input v-model="inputUrl" type="url" placeholder="https://… 或先上传文件" />
        <input type="file" accept="image/*" @change="onFile" />
        <img v-if="inputPreview" :src="inputPreview" alt="input preview" class="input-preview" />
        <span v-if="!live.isActive.value" class="field-hint">
          Mock 模式：会保存并使用你的图片地址，但成片仍是固定演示视频（不是真换脸）。要真生成请用「真实生成」+ 官网 Token。
        </span>
        <span v-else class="field-hint">
          Live 模式：图片必须是公网 HTTPS，且通常需官网上传后的 CDN 地址；随便填图床链接可能被官方拒绝。
        </span>
      </label>

      <div v-if="tpl.features?.length" class="features">
        <p>Optional features</p>
        <label v-for="f in tpl.features" :key="f.name" class="feat">
          <input v-model="selectedFeatures" type="checkbox" :value="f.name" />
          {{ f.name }} (+💎 {{ f.extra_cost }})
        </label>
      </div>

      <div class="actions">
        <button type="button" class="btn btn-primary" :disabled="busy" @click="generate">
          {{
            busy
              ? 'Generating…'
              : live.isActive.value
                ? 'Generate (Live)'
                : auth.user.value
                  ? 'Generate'
                  : 'Sign in to Generate'
          }}
        </button>
        <button
          v-if="auth.user.value"
          type="button"
          class="btn btn-ghost"
          @click="toggleFavorite"
        >
          {{ favorited ? '★ Favorited' : '☆ Favorite' }}
        </button>
      </div>
      <AuthModal v-model="showAuth" />

      <div v-if="job" class="progress card">
        <p>
          Status: {{ job.status }} · {{ job.progress }}%
          <span v-if="job.duration"> · {{ job.duration }}s</span>
          <span v-if="job.extend_count"> · 已延长 {{ job.extend_count }} 次</span>
        </p>
        <img v-if="job.input_url" :src="jobInputDisplay" class="input-preview" alt="used input" />
        <div class="bar"><div class="fill" :style="{ width: job.progress + '%' }" /></div>
        <p v-if="job.status === 'completed' && !live.isActive.value" class="out-label">
          ↓ 演示成片（固定样片，与左侧输入无关；非换脸结果）
        </p>
        <video
          v-if="job.status === 'completed' && job.output_url"
          :src="job.output_url"
          controls
          playsinline
          class="out"
        />
        <div v-if="job.status === 'completed'" class="post">
          <button type="button" class="btn btn-ghost" :disabled="busy" @click="extendJob">
            Extend +8s (+💎 {{ tpl.extend_cost ?? 15 }})
          </button>
          <button type="button" class="btn btn-ghost" @click="toggleLike">{{ job.liked ? '♥ Liked' : '♡ Like' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const slug = computed(() => String(route.params.slug))
const { api } = useApi()
const auth = useAuth()
const live = useGenspicyLive()
const { create, poll, extend, setLike } = useGeneration()

onMounted(() => live.loadTokenFromStorage())

type TemplateDetail = {
  id: string
  slug: string
  template_name: string
  cover_url: string
  tags: string[]
  generate_mode: string
  duration: number
  base_cost: number
  extend_cost?: number
  input_medias?: { url: string }[]
  features: { name: string; extra_cost: number }[]
  is_favorited?: boolean
}

const tpl = ref<TemplateDetail | null>(null)
const pending = ref(true)
const inputUrl = ref('')
const inputPreview = computed(() => {
  const u = inputUrl.value.trim()
  if (!u) return ''
  if (u.startsWith('/')) return u
  return u
})
const jobInputDisplay = computed(() => {
  const u = job.value?.input_url || ''
  if (u.startsWith('/')) return u
  return u
})
const selectedFeatures = ref<string[]>([])
const busy = ref(false)
const job = ref<Awaited<ReturnType<typeof poll>> | null>(null)
const favorited = ref(false)
const showAuth = ref(false)

const totalCost = computed(() => {
  if (!tpl.value) return 0
  let c = tpl.value.base_cost
  for (const name of selectedFeatures.value) {
    const f = tpl.value.features.find((x) => x.name === name)
    if (f) c += f.extra_cost
  }
  return c
})

async function load() {
  pending.value = true
  try {
    const data = await api<{ item: TemplateDetail }>('generation-template.get', {
      query: { slug: slug.value },
    })
    tpl.value = data.item
    favorited.value = Boolean(data.item.is_favorited)
    if (!inputUrl.value) {
      inputUrl.value =
        data.item.input_medias?.[0]?.url ||
        'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=640'
    }
  } catch {
    tpl.value = null
  } finally {
    pending.value = false
  }
}

async function generate() {
  if (!tpl.value) return
  if (live.isActive.value) {
    /* official API uses live token only */
  } else if (!auth.user.value) {
    showAuth.value = true
    return
  }
  if (!live.isActive.value && auth.user.value && auth.user.value.diamonds < totalCost.value) {
    alert(`钻石不足：需要 ${totalCost.value}，当前 ${auth.user.value.diamonds}。可到 Profile 点「+200 demo diamonds」。`)
    return
  }
  busy.value = true
  job.value = null
  try {
    const item = await create(tpl.value.id, inputUrl.value, selectedFeatures.value)
    job.value = item
    await poll(item.id, (j) => {
      job.value = j
    })
  } catch (e) {
    alert(e instanceof Error ? e.message : 'Generate failed')
  } finally {
    busy.value = false
  }
}

async function onFile(ev: Event) {
  const file = (ev.target as HTMLInputElement).files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await $fetch<{ code: number; data: { url: string }; message: string }>(
      '/api/media/upload',
      { method: 'POST', body: fd },
    )
    if (res.code !== 0) throw new Error(res.message)
    inputUrl.value = res.data.url
  } catch (e) {
    alert(e instanceof Error ? e.message : '上传失败')
  }
}

async function extendJob() {
  if (!job.value) return
  busy.value = true
  try {
    const item = await extend(job.value.id)
    job.value = item
    await poll(item.id, (j) => {
      job.value = j
    })
    if (live.isActive.value) await live.verify()
    else {
      const whoami = await api<{ user: typeof auth.user.value }>('user.whoami')
      auth.user.value = whoami.user
    }
  } catch (e) {
    alert(e instanceof Error ? e.message : 'Extend failed')
  } finally {
    busy.value = false
  }
}

async function toggleLike() {
  if (!job.value) return
  const liked = !job.value.liked
  const data = await setLike(job.value.id, liked)
  job.value = data
}

async function toggleFavorite() {
  if (!tpl.value) return
  const next = !favorited.value
  await api('generation-template-favorite.toggle', {
    method: 'POST',
    body: { template_id: tpl.value.id, favorited: next },
  })
  favorited.value = next
}

watch(slug, load, { immediate: true })
</script>

<style scoped>
.detail {
  display: grid;
  grid-template-columns: minmax(200px, 320px) 1fr;
  gap: 24px;
  align-items: start;
}

@media (max-width: 768px) {
  .detail {
    grid-template-columns: 1fr;
  }
}

.preview img {
  width: 100%;
  border-radius: var(--radius);
  aspect-ratio: 9/16;
  object-fit: cover;
}

.panel h1 {
  margin: 0 0 12px;
  font-size: 24px;
}

.row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.notice {
  font-size: 13px;
  line-height: 1.5;
  color: var(--muted);
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 92, 158, 0.1);
  margin-bottom: 10px;
}
.notice.live {
  background: rgba(125, 255, 179, 0.12);
  color: #b8ffd9;
}
.meta {
  color: var(--muted);
  font-size: 14px;
}
.warn {
  display: block;
  color: #ff8fa8;
  margin-top: 6px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 16px 0;
  font-size: 13px;
}

.field input {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--divider);
  background: var(--surface);
  color: var(--text);
}

.features {
  margin-bottom: 16px;
}

.feat {
  display: flex;
  gap: 8px;
  margin: 6px 0;
  font-size: 14px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.hint {
  font-size: 13px;
  color: var(--muted);
}

.progress {
  margin-top: 20px;
  padding: 16px;
}

.bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  overflow: hidden;
  margin: 8px 0 12px;
}

.fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-strong));
  transition: width 0.3s ease;
}

.out {
  width: 100%;
  max-height: 360px;
  border-radius: 12px;
}

.input-preview {
  max-width: 160px;
  max-height: 200px;
  border-radius: 10px;
  margin-top: 8px;
  object-fit: cover;
}
.field-hint {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
}
.post {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.state {
  padding: 32px;
  text-align: center;
  color: var(--muted);
}
</style>
