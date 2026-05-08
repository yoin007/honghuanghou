<template>
  <section class="metric-grid">
    <button
      v-for="(card, index) in cards"
      :key="card.label"
      class="metric-card"
      :style="{ '--accent': accents[index % accents.length] }"
      type="button"
      @click="handleClick(card)"
    >
      <span>{{ card.label }}</span>
      <strong>{{ card.value }}<small>{{ card.unit }}</small></strong>
      <i></i>
    </button>
  </section>
</template>

<script setup>
const props = defineProps({
  cards: {
    type: Array,
    default: () => []
  },
  accents: {
    type: Array,
    default: () => ['#38bdf8', '#fbbf24', '#34d399', '#f472b6', '#f87171']
  }
})

const emit = defineEmits(['click'])

const handleClick = (card) => {
  emit('click', card.route, card)
}
</script>

<style scoped>
.metric-grid {
  display: grid;
  gap: 14px;
  margin-bottom: 18px;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}

.metric-card {
  position: relative;
  min-height: 112px;
  padding: 18px;
  color: #e2e8f0;
  text-align: left;
  cursor: pointer;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 62%);
  border-radius: 8px;
  background: linear-gradient(155deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.62));
  overflow: hidden;
}

.metric-card span,
.metric-card strong {
  position: relative;
  z-index: 1;
}

.metric-card span {
  color: #94a3b8;
}

.metric-card strong {
  display: block;
  margin-top: 16px;
  color: #f8fafc;
  font-size: 32px;
  line-height: 1;
}

.metric-card small {
  margin-left: 5px;
  color: #cbd5e1;
  font-size: 14px;
}

.metric-card i {
  position: absolute;
  right: -34px;
  bottom: -38px;
  width: 110px;
  height: 110px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent), transparent 74%);
  filter: blur(8px);
}
</style>
