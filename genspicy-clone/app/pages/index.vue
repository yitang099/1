<template>
  <div>
    <section class="hero">
      <h1>Explore AI Video Templates</h1>
      <p>Full catalog locally (import with <code>pnpm import:templates</code>). Payment disabled.</p>
      <input v-model="q" type="search" class="search" placeholder="Search templates…" />
    </section>
    <TemplateFeed :query="feedQuery" mode="list" />
  </div>
</template>

<script setup lang="ts">
const q = ref('')
const feedQuery = computed(() => (q.value.trim() ? { q: q.value.trim() } : {}))
</script>

<style scoped>
.hero {
  margin-bottom: 16px;
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 28px;
}
.hero p {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 14px;
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
</style>
