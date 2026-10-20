<template>
  <div class="card panel">
    <h1>Affiliate</h1>
    <p class="lead">Referral tracking works locally. Payouts disabled (no payment).</p>
    <p v-if="!auth.user.value" class="muted">Sign in to get your referral link.</p>
    <template v-else>
      <label class="field">
        <span>Your referral link</span>
        <input readonly :value="link" />
      </label>
      <button type="button" class="btn btn-primary" @click="copy">Copy link</button>
      <p v-if="copied" class="ok">Copied!</p>
      <ul class="stats">
        <li><strong>{{ stats?.clicks ?? 0 }}</strong> clicks</li>
        <li><strong>{{ stats?.signups ?? 0 }}</strong> signups</li>
        <li><strong>$0</strong> earnings (payout disabled)</li>
      </ul>
    </template>
  </div>
</template>

<script setup lang="ts">
const auth = useAuth()
const { api } = useApi()
const copied = ref(false)
const stats = ref<{ clicks: number; signups: number } | null>(null)

const link = computed(() => {
  const code = auth.user.value?.referral_code || auth.user.value?.uuid?.slice(0, 8) || 'guest'
  if (import.meta.client) return `${window.location.origin}/?ref=${code}`
  return `http://localhost:3000/?ref=${code}`
})

async function loadStats() {
  if (!auth.user.value) return
  const data = await api<{ clicks: number; signups: number }>('affiliate.stats.get')
  stats.value = data
}

async function copy() {
  if (!import.meta.client) return
  await navigator.clipboard.writeText(link.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}

watch(
  () => auth.user.value,
  () => loadStats(),
  { immediate: true },
)
</script>

<style scoped>
.panel {
  padding: 24px;
  max-width: 560px;
}
.lead {
  color: var(--muted);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 16px 0;
}
.field input {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--divider);
  background: rgba(0, 0, 0, 0.2);
  color: var(--text);
}
.stats {
  margin-top: 24px;
  padding-left: 18px;
  color: var(--muted);
}
.ok {
  color: #7dffb3;
  font-size: 13px;
}
.muted {
  color: var(--muted);
}
</style>
