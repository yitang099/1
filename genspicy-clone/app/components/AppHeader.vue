<template>
  <header class="header card">
    <NuxtLink to="/" class="brand">
      <span class="logo">G</span>
      <span>{{ siteName }}</span>
      <span class="badge">Local v2</span>
    </NuxtLink>
    <nav class="nav">
      <NuxtLink to="/">Explore</NuxtLink>
      <NuxtLink to="/drama">Drama</NuxtLink>
      <NuxtLink to="/videos">Videos</NuxtLink>
      <NuxtLink to="/create">Create</NuxtLink>
      <NuxtLink to="/tools">Tools</NuxtLink>
      <NuxtLink to="/user/favorites">Favorites</NuxtLink>
      <NuxtLink to="/user/creations">Creations</NuxtLink>
      <NuxtLink to="/affiliate">Affiliate</NuxtLink>
      <NuxtLink to="/pricing">Pricing</NuxtLink>
    </nav>
    <div class="actions">
      <template v-if="auth.user.value">
        <NuxtLink to="/user/profile" class="profile">{{ auth.user.value.name }}</NuxtLink>
        <span class="diamonds">💎 {{ auth.user.value.diamonds }}</span>
        <span class="vip">VIP {{ auth.user.value.vip_level }}</span>
        <button type="button" class="btn btn-ghost" @click="auth.signOut()">Sign out</button>
      </template>
      <button v-else type="button" class="btn btn-primary" @click="showAuth = true">Sign in</button>
    </div>
    <AuthModal v-model="showAuth" />
  </header>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
const siteName = config.public.siteName
const auth = useAuth()
const showAuth = ref(false)
</script>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 20;
  margin: 8px 16px;
  padding: 10px 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  background: rgba(26, 26, 26, 0.92);
  backdrop-filter: blur(8px);
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}
.logo {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(282deg, #ff75ba, var(--accent-strong));
  display: grid;
  place-items: center;
}
.badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 6px;
  background: rgba(255, 92, 158, 0.2);
  color: var(--accent);
  font-weight: 600;
}
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  flex: 1;
  font-size: 13px;
  color: var(--muted);
}
.nav a.router-link-active {
  color: var(--text);
  font-weight: 600;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}
.profile {
  font-size: 13px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.diamonds {
  font-size: 13px;
  font-weight: 600;
}
.vip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
}
</style>
