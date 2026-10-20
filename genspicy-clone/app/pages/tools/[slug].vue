<template>
  <div>
    <h1>{{ meta?.title || 'Tool' }}</h1>
    <p class="lead">{{ meta?.blurb || 'Template collection' }}</p>
    <NuxtLink
      v-if="meta && 'featuredSlug' in meta && meta.featuredSlug"
      :to="`/template/${meta.featuredSlug}`"
      class="btn btn-primary featured"
    >
      打开主推换脸模板
    </NuxtLink>
    <TemplateFeed v-if="meta" :query="{ q: meta.tag }" mode="list" />
    <p v-else class="lead">Unknown tool page.</p>
  </div>
</template>

<script setup lang="ts">
import { toolPages } from '~/utils/site-config'

const route = useRoute()
const slug = computed(() => String(route.params.slug))
const meta = computed(() => toolPages[slug.value])
</script>

<style scoped>
.lead {
  color: var(--muted);
  margin-bottom: 16px;
}
.featured {
  display: inline-flex;
  margin-bottom: 16px;
}
</style>
