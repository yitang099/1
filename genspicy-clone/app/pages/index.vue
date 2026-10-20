<template>
  <div>
    <section class="hero">
      <h1>AI Video Templates</h1>
      <p>Local clone — explore templates, generate with diamonds (no Stripe in v1).</p>
      <input v-model="q" type="search" class="search" placeholder="Search templates…" />
    </section>
    <div v-if="pending" class="state">Loading templates…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>
    <div v-else class="grid">
      <TemplateCard v-for="t in items" :key="t.id" :template="t" />
    </div>
  </div>
</template>

<script setup lang="ts">
const { homeTemplates } = useApi()
const q = ref('')
const items = ref<
  {
    id: string
    slug: string
    template_name: string
    cover_url: string
    duration: number
    base_cost: number
    card_tags?: string[]
  }[]
>([])
const pending = ref(true)
const error = ref('')

async function load() {
  pending.value = true
  error.value = ''
  try {
    const data = await homeTemplates(1, 50)
    let list = data.items as typeof items.value
    if (q.value.trim()) {
      const needle = q.value.toLowerCase()
      list = list.filter(
        (t) =>
          t.template_name.toLowerCase().includes(needle) ||
          (t as { tags?: string[] }).tags?.some((tag) => tag.toLowerCase().includes(needle)),
      )
    }
    items.value = list
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load'
  } finally {
    pending.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout> | undefined
watch(q, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(load, 300)
})
onMounted(load)
</script>

<style scoped>
.hero {
  margin-bottom: 20px;
}

.hero h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.hero p {
  margin: 0 0 16px;
  color: var(--muted);
}

.search {
  width: 100%;
  max-width: 420px;
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid var(--divider);
  background: var(--surface);
  color: var(--text);
}

.state {
  padding: 24px;
  text-align: center;
  color: var(--muted);
}

.state.err {
  color: #ff6b8a;
}
</style>
