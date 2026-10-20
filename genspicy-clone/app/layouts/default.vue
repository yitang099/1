<template>
  <div class="shell">
    <AppHeader />
    <main class="page">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
}
</style>
