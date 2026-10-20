<template>
  <div>
    <h1>My Creations</h1>
    <p v-if="!auth.user.value" class="muted">Continue as guest to see your generations.</p>
    <div v-else-if="pending" class="muted">Loading…</div>
    <div v-else-if="!items.length" class="muted">No creations yet — generate from a template.</div>
    <ul v-else class="list">
      <li v-for="j in items" :key="j.id" class="card item">
        <div>
          <strong>{{ j.template_name }}</strong>
          <p>{{ j.status }} · {{ j.progress }}% · {{ formatDate(j.created_at) }}</p>
        </div>
        <div class="item-actions">
          <video
            v-if="j.status === 'completed' && j.output_url"
            :src="j.output_url"
            muted
            playsinline
            class="thumb"
          />
          <button type="button" class="btn btn-ghost" @click="remove(j.id)">Delete</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
const auth = useAuth()
const { api } = useApi()
const pending = ref(false)
const items = ref<
  {
    id: string
    template_name: string
    status: string
    progress: number
    output_url?: string
    created_at: number
  }[]
>([])

function formatDate(ts: number) {
  return new Date(ts).toLocaleString()
}

async function load() {
  if (!auth.user.value) return
  pending.value = true
  try {
    const data = await api<{ items: typeof items.value }>('user-generation-content.list', {
      query: { page: 1, page_size: 50 },
    })
    items.value = data.items
  } finally {
    pending.value = false
  }
}

async function remove(id: string) {
  await api('user-generation-content.delete', { method: 'POST', body: { id } })
  await load()
}

watch(
  () => auth.user.value,
  () => load(),
  { immediate: true },
)
</script>

<style scoped>
h1 {
  margin: 0 0 8px;
}

.muted {
  color: var(--muted);
}

.list {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item {
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.item p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--muted);
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.thumb {
  width: 72px;
  height: 128px;
  object-fit: cover;
  border-radius: 8px;
  background: #111;
}
</style>
