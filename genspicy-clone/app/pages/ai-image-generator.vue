<template>
  <div>
    <h1>AI Image Generator</h1>
    <p class="lead">Image-oriented templates and tools (local mock).</p>
    <TemplateFeed mode="list" :query="{ q: 'photo' }" />
  </div>
</template>

<style scoped>
.lead {
  color: var(--muted);
  margin-bottom: 16px;
}
</style>
