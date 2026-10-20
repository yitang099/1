<template>
  <div v-if="modelValue" class="overlay" @click.self="close">
    <div class="modal card">
      <div class="tabs">
        <button type="button" :class="{ active: tab === 'guest' }" @click="tab = 'guest'">Guest</button>
        <button type="button" :class="{ active: tab === 'email' }" @click="tab = 'email'">Email</button>
      </div>
      <template v-if="tab === 'guest'">
        <p class="muted">500 diamonds · VIP 2 · no payment in local build</p>
        <div class="choices">
          <button type="button" class="choice" @click="guest('female')">Female</button>
          <button type="button" class="choice" @click="guest('male')">Male</button>
        </div>
      </template>
      <template v-else>
        <label class="field">
          Email
          <input v-model="email" type="email" placeholder="you@example.com" />
        </label>
        <label class="field">
          Display name
          <input v-model="name" type="text" placeholder="Optional" />
        </label>
        <div class="choices">
          <button type="button" class="choice" @click="gender = 'female'">Female</button>
          <button type="button" class="choice" @click="gender = 'male'">Male</button>
        </div>
        <button type="button" class="btn btn-primary full" :disabled="!email || !gender" @click="emailSignIn">
          Continue
        </button>
      </template>
      <button type="button" class="btn btn-ghost full" @click="close">Cancel</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()
const auth = useAuth()
const tab = ref<'guest' | 'email'>('guest')
const email = ref('')
const name = ref('')
const gender = ref<'male' | 'female' | ''>('')

function close() {
  emit('update:modelValue', false)
}

async function guest(g: 'male' | 'female') {
  await auth.guestSignUp(g)
  close()
}

async function emailSignIn() {
  if (!gender.value) return
  await auth.emailSignIn({
    email: email.value,
    gender: gender.value,
    name: name.value || undefined,
  })
  close()
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: grid;
  place-items: center;
  z-index: 50;
  padding: 16px;
}
.modal {
  width: min(420px, 100%);
  padding: 20px;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.tabs button {
  flex: 1;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid var(--divider);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.tabs button.active {
  color: var(--text);
  border-color: var(--accent);
}
.muted {
  color: var(--muted);
  font-size: 13px;
}
.choices {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 12px 0;
}
.choice {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--divider);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  cursor: pointer;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  margin-bottom: 8px;
}
.field input {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--divider);
  background: var(--surface);
  color: var(--text);
}
.full {
  width: 100%;
  margin-top: 8px;
}
</style>
