<template>
  <div>
    <h1>Pricing</h1>
    <p class="lead">Plans shown for parity with Genspicy. Checkout is disabled in this local build.</p>
    <div class="plans">
      <div v-for="plan in plans" :key="plan.name" class="card plan">
        <h2>{{ plan.name }}</h2>
        <p class="price">{{ plan.price }}</p>
        <ul>
          <li v-for="f in plan.features" :key="f">{{ f }}</li>
        </ul>
        <button type="button" class="btn btn-ghost" disabled>Payment disabled (v2 local)</button>
      </div>
    </div>
    <p class="hint">Use Profile → “+200 demo diamonds” or guest signup balance for testing.</p>
  </div>
</template>

<script setup lang="ts">
const plans = [
  { name: 'Starter', price: '$9 / mo', features: ['500 diamonds', 'VIP 1', 'Standard queue'] },
  { name: 'Pro', price: '$29 / mo', features: ['2000 diamonds', 'VIP 2', 'HD features'] },
  { name: 'Ultra', price: '$79 / mo', features: ['8000 diamonds', 'VIP 3', 'Drama Pro access'] },
]
</script>

<style scoped>
.lead {
  color: var(--muted);
}
.plans {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin: 20px 0;
}
.plan {
  padding: 20px;
}
.price {
  font-size: 22px;
  font-weight: 700;
}
.hint {
  font-size: 13px;
  color: var(--muted);
}
</style>
