<template>
  <div>
    <div v-if="pending && !items.length" class="state">Loading…</div>
    <div v-else-if="error" class="state err">{{ error }}</div>
    <div v-else class="grid">
      <TemplateCard v-for="t in items" :key="t.id" :template="t" />
    </div>
    <div v-if="hasMore" class="more">
      <button type="button" class="btn btn-ghost" :disabled="pending" @click="loadMore">
        {{ pending ? 'Loading…' : 'Load more' }}
      </button>
      <span class="count">{{ items.length }} / {{ total }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  mode?: 'home' | 'list' | 'favorites'
  query?: Record<string, string | number>
}>()

const { api, homeTemplates } = useApi()
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
const page = ref(1)
const total = ref(0)
const pending = ref(false)
const error = ref('')
const pageSize = 24

const hasMore = computed(() => items.value.length < total.value)

async function fetchPage(p: number, append: boolean) {
  pending.value = true
  error.value = ''
  try {
    let data: { items: typeof items.value; total: number }
    if (props.mode === 'favorites') {
      data = await api<{ items: typeof items.value; total: number }>(
        'generation-template-favorite.list',
        { query: { page: p, page_size: pageSize } },
      )
    } else if (props.mode === 'home' && !props.query) {
      data = (await homeTemplates(p, pageSize)) as typeof data
    } else {
      data = await api<{ items: typeof items.value; total: number }>('generation-template.list', {
        query: { page: p, page_size: pageSize, ...props.query },
      })
    }
    total.value = data.total
    items.value = append ? [...items.value, ...data.items] : data.items
    page.value = p
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Load failed'
  } finally {
    pending.value = false
  }
}

function loadMore() {
  if (!hasMore.value || pending.value) return
  fetchPage(page.value + 1, true)
}

watch(
  () => props.query,
  () => {
    page.value = 1
    fetchPage(1, false)
  },
  { deep: true, immediate: true },
)
</script>

<style scoped>
.state {
  padding: 24px;
  text-align: center;
  color: var(--muted);
}
.state.err {
  color: #ff6b8a;
}
.more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}
.count {
  font-size: 13px;
  color: var(--muted);
}
</style>
