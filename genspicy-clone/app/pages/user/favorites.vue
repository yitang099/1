<template>
  <div>
    <h1>Favorites</h1>
    <p v-if="!auth.user.value" class="muted">Sign in to sync favorites.</p>
    <TemplateFeed v-else mode="favorites" />
  </div>
</template>

<script setup lang="ts">
const auth = useAuth()
</script>

<style scoped>
.muted {
  color: var(--muted);
}
</style>
