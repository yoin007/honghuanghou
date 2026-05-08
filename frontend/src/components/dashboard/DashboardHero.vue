<template>
  <header class="hero-band">
    <div>
      <span v-if="kicker" class="kicker">{{ kicker }}</span>
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <slot />
  </header>
</template>

<script setup>
defineProps({
  kicker: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.hero-band {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.72));
}

.kicker {
  color: #67e8f9;
  font-size: 12px;
}

h1 {
  margin: 8px 0;
  color: #f8fafc;
  font-size: 40px;
  line-height: 1.08;
  letter-spacing: 0;
}

p {
  max-width: 720px;
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
}

@media (max-width: 980px) {
  .hero-band {
    flex-direction: column;
    align-items: stretch;
  }

  h1 {
    font-size: 34px;
  }
}
</style>