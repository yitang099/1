<template>
  <div>
    <h1>AI Tools</h1>
    <p class="lead">Marketing tool hubs mapped to template tag filters (mirrors genspicy.ai/tools).</p>
    <ul class="list">
      <li v-for="(meta, slug) in toolPages" :key="slug">
        <NuxtLink :to="`/tools/${slug}`" class="card link">
          <strong>{{ meta.title }}</strong>
          <span>{{ meta.blurb }}</span>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { toolPages } from '~/utils/site-config'
</script>

<style scoped>
.lead {
  color: var(--muted);
}
.list {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 10px;
}
.link {
  display: block;
  padding: 14px 16px;
}
.link span {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  color: var(--muted);
}
</style>
