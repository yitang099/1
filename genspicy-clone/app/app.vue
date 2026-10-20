<template>
  <NuxtLayout>
    <NuxtRouteAnnouncer />
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
const auth = useAuth()
const route = useRoute()
const { api } = useApi()

onMounted(async () => {
  const refCode = String(route.query.ref || '')
  if (refCode) {
    captureReferral(refCode)
    try {
      await api('affiliate.click.track', { method: 'POST', body: { referral_code: refCode } })
    } catch {
      /* ignore */
    }
  }
  await auth.init()
})
</script>
