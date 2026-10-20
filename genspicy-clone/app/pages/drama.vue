<template>
  <div>
    <h1>Drama Pro</h1>
    <p class="lead">Long-form drama templates (60s+). Same generate flow, mock output locally.</p>
    <TemplateFeed :query="{ template_type: 'drama' }" mode="list" />
  </div>
</template>

<style scoped>
h1 {
  margin: 0 0 8px;
}
.lead {
  color: var(--muted);
  margin: 0 0 16px;
}
</style>
