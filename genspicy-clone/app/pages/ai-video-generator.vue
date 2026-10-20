<template>
  <div>
    <h1>AI Video Generator</h1>
    <p class="lead">Same as Genspicy landing — routes into local create flow.</p>
    <NuxtLink to="/create" class="btn btn-primary">Start creating</NuxtLink>
    <TemplateFeed mode="list" :query="{ generate_mode: 'image_to_video' }" />
  </div>
</template>

<style scoped>
.lead {
  color: var(--muted);
  margin-bottom: 16px;
}
</style>
