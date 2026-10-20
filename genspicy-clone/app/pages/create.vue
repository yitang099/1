<template>
  <div>
    <h1>Create</h1>
    <p class="lead">Choose a mode — image-to-video, text-to-video, or drama.</p>
    <div class="modes">
      <button
        v-for="m in modes"
        :key="m.key"
        type="button"
        class="chip"
        :class="{ active: mode === m.key }"
        @click="mode = m.key"
      >
        {{ m.label }}
      </button>
    </div>
    <TemplateFeed mode="list" :query="modeQuery" />
  </div>
</template>

<script setup lang="ts">
const modes = [
  { key: 'all', label: 'All', query: {} },
  { key: 'i2v', label: 'Image → Video', query: { generate_mode: 'image_to_video' } },
  { key: 't2v', label: 'Text → Video', query: { generate_mode: 'r2v_txt' } },
  { key: 'drama', label: 'Drama', query: { template_type: 'drama' } },
] as const

const mode = ref<(typeof modes)[number]['key']>('all')
const modeQuery = computed(() => {
  const m = modes.find((x) => x.key === mode.value)
  return m?.query || {}
})
</script>

<style scoped>
.lead {
  color: var(--muted);
}
.modes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 16px;
}
.chip {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--divider);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.chip.active {
  border-color: var(--accent);
  color: var(--text);
}
</style>
