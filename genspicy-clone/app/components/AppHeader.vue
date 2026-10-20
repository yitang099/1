<template>
  <header class="header card">
    <NuxtLink to="/" class="brand">
      <span class="logo">G</span>
      <span>{{ siteName }}</span>
      <span class="badge">Local v1</span>
    </NuxtLink>
    <nav class="nav">
      <NuxtLink to="/">Explore</NuxtLink>
      <NuxtLink to="/create">Create</NuxtLink>
      <NuxtLink to="/user/creations">My Creations</NuxtLink>
      <NuxtLink to="/affiliate">Affiliate</NuxtLink>
    </nav>
    <div class="actions">
      <template v-if="auth.user.value">
        <span class="diamonds" title="Diamonds (no payment in v1)">💎 {{ auth.user.value.diamonds }}</span>
        <span class="vip">VIP {{ auth.user.value.vip_level }}</span>
        <button type="button" class="btn btn-ghost" @click="auth.signOut()">Sign out</button>
      </template>
      <button v-else type="button" class="btn btn-primary" @click="showGender = true">
        Continue as Guest
      </button>
    </div>
    <GenderModal v-model="showGender" @pick="onGender" />
  </header>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
const siteName = config.public.siteName
const auth = useAuth()
const showGender = ref(false)

async function onGender(g: 'male' | 'female') {
  showGender.value = false
  await auth.guestSignUp(g)
}
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
  gap: 12px;
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
  gap: 14px;
  flex: 1;
  font-size: 14px;
  color: var(--muted);
}

.nav a.router-link-active {
  color: var(--text);
  font-weight: 600;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
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
