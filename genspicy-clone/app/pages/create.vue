<template>
  <div>
    <h1>Create</h1>
    <p class="lead">
      Pick a template from the feed to generate. This page mirrors Genspicy’s create hub (payment
      skipped in v1).
    </p>
    <div class="grid">
      <TemplateCard v-for="t in items" :key="t.id" :template="t" />
    </div>
  </div>
</template>

<script setup lang="ts">
const { homeTemplates } = useApi()
const items = ref<Awaited<ReturnType<typeof homeTemplates>>['items']>([])

onMounted(async () => {
  const data = await homeTemplates(1, 50)
  items.value = data.items
})
</script>

<style scoped>
h1 {
  margin: 0 0 8px;
}

.lead {
  color: var(--muted);
  margin: 0 0 20px;
  max-width: 560px;
}
</style>
