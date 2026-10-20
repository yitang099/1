<template>
  <div class="card panel">
    <h1>Affiliate</h1>
    <p>
      Referral program UI (local mock). Share your link — commissions are not wired in v1 (no
      payment).
    </p>
    <label class="field">
      <span>Your referral link</span>
      <input readonly :value="link" />
    </label>
    <button type="button" class="btn btn-primary" @click="copy">Copy link</button>
    <p v-if="copied" class="ok">Copied!</p>
    <ul class="stats">
      <li><strong>0</strong> signups</li>
      <li><strong>$0</strong> earnings (disabled)</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
const auth = useAuth()
const copied = ref(false)
const link = computed(() => {
  const id = auth.user.value?.uuid?.slice(0, 8) || 'guest'
  if (import.meta.client) return `${window.location.origin}/?ref=${id}`
  return `http://localhost:3000/?ref=${id}`
})

async function copy() {
  if (!import.meta.client) return
  await navigator.clipboard.writeText(link.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}
</script>

<style scoped>
.panel {
  padding: 24px;
  max-width: 560px;
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
</style>
