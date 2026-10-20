<template>
  <div>
    <h1>{{ meta?.title || category }}</h1>
    <TemplateFeed v-if="meta" :query="{ tag: meta.tag }" mode="list" />
  </div>
</template>

<script setup lang="ts">
import { templateCategories } from '~/utils/site-config'

const route = useRoute()
const category = computed(() => String(route.params.category))
const meta = computed(() => templateCategories[category.value])
</script>
