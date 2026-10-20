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
      <p class="notice">
        本地演示：点击 Generate 会模拟进度并播放<strong>示例视频</strong>（不是真实 AI 推理，也不会用你的上传图生成新片）。
      </p>
      <p class="meta">
        {{ tpl.generate_mode }} · {{ tpl.duration }}s · 💎 {{ totalCost }} (base {{ tpl.base_cost }})
        <span v-if="auth.user.value && auth.user.value.diamonds < totalCost" class="warn">
          钻石不足，请到 Profile 领取演示钻石或换更便宜的模板
        </span>
      </p>

      <label class="field">
        <span>Input image URL (mock upload)</span>
        <input v-model="inputUrl" type="url" placeholder="https://…" />
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
          {{ busy ? 'Generating…' : auth.user.value ? 'Generate' : 'Sign in to Generate' }}
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
        <p>Status: {{ job.status }} · {{ job.progress }}%</p>
        <div class="bar"><div class="fill" :style="{ width: job.progress + '%' }" /></div>
        <video
          v-if="job.status === 'completed' && job.output_url"
          :src="job.output_url"
          controls
          playsinline
          class="out"
        />
        <div v-if="job.status === 'completed'" class="post">
          <button type="button" class="btn btn-ghost" @click="extendJob">Extend (+💎 {{ tpl.extend_cost }})</button>
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
const { create, poll, extend, setLike } = useGeneration()

type TemplateDetail = {
  id: string
  slug: string
  template_name: string
  cover_url: string
  tags: string[]
  generate_mode: string
  duration: number
  base_cost: number
  features: { name: string; extra_cost: number }[]
  is_favorited?: boolean
}

const tpl = ref<TemplateDetail | null>(null)
const pending = ref(true)
const inputUrl = ref('https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=640')
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
  } catch {
    tpl.value = null
  } finally {
    pending.value = false
  }
}

async function generate() {
  if (!tpl.value) return
  if (!auth.user.value) {
    showAuth.value = true
    return
  }
  if (auth.user.value.diamonds < totalCost.value) {
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

async function extendJob() {
  if (!job.value) return
  busy.value = true
  try {
    const item = await extend(job.value.id)
    job.value = item
    await poll(item.id, (j) => {
      job.value = j
    })
    const whoami = await api<{ user: typeof auth.user.value }>('user.whoami')
    auth.user.value = whoami.user
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
