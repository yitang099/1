<template>
  <div v-if="modelValue" class="overlay" @click.self="close">
    <div class="modal card">
      <h2>Choose your gender</h2>
      <p class="muted">Guest account — 500 diamonds, VIP 2. No payment in this local build.</p>
      <div class="choices">
        <button type="button" class="choice" @click="emit('pick', 'female')">Female</button>
        <button type="button" class="choice" @click="emit('pick', 'male')">Male</button>
      </div>
      <button type="button" class="btn btn-ghost full" @click="close">Cancel</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean]; pick: ['male' | 'female'] }>()

function close() {
  emit('update:modelValue', false)
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
  width: min(400px, 100%);
  padding: 24px;
}

h2 {
  margin: 0 0 8px;
  font-size: 20px;
}

.muted {
  color: var(--muted);
  font-size: 13px;
  margin: 0 0 20px;
}

.choices {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.choice {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--divider);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  cursor: pointer;
  font-weight: 600;
}

.choice:hover {
  border-color: var(--accent);
}

.full {
  width: 100%;
}
</style>
