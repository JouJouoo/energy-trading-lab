<script setup>import { computed } from 'vue';
import { Bar, Doughnut } from 'vue-chartjs';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);
const props = defineProps({
 metrics: {
 type: Array,
 default: () => []
 }
});
const barChartData = computed(() => ({
 labels: props.metrics.map(m => m.strategy || 'Unknown'),
 datasets: [
 {
 label: 'Total Cost',
 data: props.metrics.map(m => Number(m.total_cost) || 0),
 backgroundColor: 'rgba(18, 119, 109, 0.7)',
 borderColor: 'rgba(18, 119, 109, 1)',
 borderWidth: 1,
 borderRadius: 6
 },
 {
 label: 'P2P Volume (kWh)',
 data: props.metrics.map(m => Number(m.p2p_volume_kwh) || 0),
 backgroundColor: 'rgba(37, 99, 235, 0.7)',
 borderColor: 'rgba(37, 99, 235, 1)',
 borderWidth: 1,
 borderRadius: 6
 }
 ]
}));
const barChartOptions = {
 responsive: true,
 maintainAspectRatio: false,
 plugins: {
 legend: {
 position: 'top'
 },
 title: {
 display: true,
 text: 'Strategy Comparison'
 }
 },
 scales: {
 y: {
 beginAtZero: true
 }
 }
};
const doughnutChartData = computed(() => {
 if (!props.metrics.length)
 return { labels: [], datasets: [] };
 const best = props.metrics.reduce((w, r) => {
 const wCost = Number(w.total_cost) || Infinity;
 const rCost = Number(r.total_cost) || Infinity;
 return rCost < wCost ? r : w;
 }, props.metrics[0]);
 const others = props.metrics.filter(m => m.strategy !== best.strategy);
 const othersAvgCost = others.length ? others.reduce((sum, m) => sum + (Number(m.total_cost) || 0), 0) / others.length : 0;
 return {
 labels: [best.strategy || 'Best', 'Others (Avg)'],
 datasets: [{
 data: [Number(best.total_cost) || 0, othersAvgCost],
 backgroundColor: [
 'rgba(18, 119, 109, 0.8)',
 'rgba(100, 116, 139, 0.6)'
 ],
 borderColor: [
 'rgba(18, 119, 109, 1)',
 'rgba(100, 116, 139, 1)'
 ],
 borderWidth: 2
 }]
 };
});
const doughnutChartOptions = {
 responsive: true,
 maintainAspectRatio: false,
 plugins: {
 legend: {
 position: 'bottom'
 },
 title: {
 display: true,
 text: 'Cost Comparison'
 }
 }
};
</script>

<template>
  <div class="metrics-chart">
    <div class="chart-container">
      <Bar :data="barChartData" :options="barChartOptions" />
    </div>
    <div class="chart-container small">
      <Doughnut :data="doughnutChartData" :options="doughnutChartOptions" />
    </div>
  </div>
</template>

<style scoped>
.metrics-chart {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.chart-container {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
  height: 300px;
}

.chart-container.small {
  height: 260px;
}

@media (max-width: 900px) {
  .metrics-chart {
    grid-template-columns: 1fr;
  }
}
</style>
