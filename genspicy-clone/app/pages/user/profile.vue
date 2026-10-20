<template>
  <div class="card panel">
    <h1>Profile</h1>
    <p v-if="!auth.user.value" class="muted">Sign in to edit profile.</p>
    <template v-else>
      <label class="field">
        Name
        <input v-model="name" type="text" />
      </label>
      <label class="field">
        Photo URL
        <input v-model="photo" type="url" />
      </label>
      <p class="meta">{{ auth.user.value.email }} · {{ auth.user.value.role }}</p>
      <button type="button" class="btn btn-primary" @click="save">Save</button>
      <button type="button" class="btn btn-ghost" @click="grant">+200 demo diamonds</button>
    </template>
  </div>
</template>

<script setup lang="ts">
const auth = useAuth()
const { api } = useApi()
const name = ref('')
const photo = ref('')

watch(
  () => auth.user.value,
  (u) => {
    name.value = u?.name || ''
    photo.value = u?.photo_url || ''
  },
  { immediate: true },
)

async function save() {
  const data = await api<{ user: typeof auth.user.value }>('user.profile.update', {
    method: 'POST',
    body: { name: name.value, photo_url: photo.value },
  })
  auth.user.value = data.user
}

async function grant() {
  const data = await api<{ user: typeof auth.user.value }>('wallet.diamonds.grant-demo', {
    method: 'POST',
  })
  auth.user.value = data.user
}
</script>

<style scoped>
.panel {
  padding: 24px;
  max-width: 480px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.field input {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--divider);
  background: var(--surface);
  color: var(--text);
}
.meta {
  font-size: 13px;
  color: var(--muted);
}
.muted {
  color: var(--muted);
}
</style>
