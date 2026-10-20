<template>
  <NuxtLink :to="`/template/${template.slug}`" class="card tile">
    <div class="cover">
      <img :src="template.cover_url" :alt="template.template_name" loading="lazy" />
      <div v-if="template.card_tags?.length" class="tags">
        <span v-for="tag in template.card_tags" :key="tag" class="tag">{{ tag }}</span>
      </div>
    </div>
    <div class="meta">
      <h3>{{ template.template_name }}</h3>
      <p>{{ template.duration }}s · 💎 {{ template.base_cost }}</p>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
defineProps<{
  template: {
    slug: string
    template_name: string
    cover_url: string
    duration: number
    base_cost: number
    card_tags?: string[]
  }
}>()
</script>

<style scoped>
.tile {
  overflow: hidden;
  transition: transform 0.15s ease;
}

.tile:hover {
  transform: translateY(-2px);
}

.cover {
  position: relative;
  aspect-ratio: 9 / 16;
  background: #111;
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.tags {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.meta {
  padding: 10px 12px 14px;
}

.meta h3 {
  margin: 0 0 4px;
  font-size: 14px;
  line-height: 1.3;
}

.meta p {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}
</style>
