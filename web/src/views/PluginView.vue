<template>
  <div class="plugin-view">
    <header class="plugin-header">
      <h1>插件浏览</h1>
      <p class="plugin-subtitle">
        运行时发现所有算法模板和仿真场景,新增算法 / 电网案例 = 复制一个文件夹
        + 写一个 <code>TEMPLATE.md</code> / <code>SCENARIO.md</code>。
        详见 <code>docs/skills-protocol.md</code> 与 <code>docs/scenarios-protocol.md</code>。
      </p>
      <div class="plugin-actions">
        <button class="primary" @click="refresh" :disabled="loading">
          {{ loading ? "刷新中..." : "刷新" }}
        </button>
        <button @click="copyAsJson" :disabled="loading || (!templates.length && !scenarios.length)">
          复制为 JSON
        </button>
      </div>
    </header>

    <section class="plugin-section">
      <h2>算法模板 (Algorithm Templates)</h2>
      <p v-if="!templates.length && !loading" class="empty">未发现算法模板。</p>
      <div v-else class="card-grid">
        <div
          v-for="t in templates"
          :key="t.name"
          class="card"
          :class="{ shadow: true }"
        >
          <div class="card-header">
            <span class="badge">{{ t.family }}</span>
            <h3 class="card-title">{{ t.display_name }}</h3>
            <span class="card-name">@{{ t.name }}</span>
          </div>
          <p class="card-body">{{ t.description || "(无描述)" }}</p>
          <ul class="card-meta">
            <li><strong>文件:</strong> <code>{{ t.file_name }}</code></li>
            <li v-if="t.parameters && Object.keys(t.parameters).length">
              <strong>默认参数:</strong>
              <code v-for="(v, k) in t.parameters" :key="k">{{ k }}={{ v }}</code>
            </li>
            <li v-if="t.tags && t.tags.length">
              <strong>标签:</strong>
              <span v-for="tag in t.tags" :key="tag" class="tag">{{ tag }}</span>
            </li>
            <li class="card-source"><strong>来源:</strong> <code>{{ t.source }}</code></li>
          </ul>
        </div>
      </div>
    </section>

    <section class="plugin-section">
      <h2>仿真场景 (Scenarios)</h2>
      <p v-if="!scenarios.length && !loading" class="empty">未发现仿真场景。</p>
      <div v-else class="card-grid">
        <div
          v-for="s in scenarios"
          :key="s.name"
          class="card"
          :class="{ shadow: true }"
        >
          <div class="card-header">
            <span class="badge">{{ s.bus_count }} buses</span>
            <h3 class="card-title">{{ s.display_name }}</h3>
            <span class="card-name">@{{ s.name }}</span>
          </div>
          <ul class="card-meta">
            <li><strong>基准电压:</strong> {{ s.base_voltage_kv }} kV</li>
            <li>
              <strong>电压限值:</strong>
              <code>{{ s.voltage_limits[0] }} ~ {{ s.voltage_limits[1] }} pu</code>
            </li>
            <li><strong>拓扑来源:</strong> {{ s.topology_source }}</li>
            <li v-if="s.tags && s.tags.length">
              <strong>标签:</strong>
              <span v-for="tag in s.tags" :key="tag" class="tag">{{ tag }}</span>
            </li>
            <li class="card-source"><strong>来源:</strong> <code>{{ s.source }}</code></li>
          </ul>
        </div>
      </div>
    </section>

    <section v-if="error" class="plugin-section error">
      <h2>错误</h2>
      <p>{{ error }}</p>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client.js'

const templates = ref([])
const scenarios = ref([])
const loading = ref(false)
const error = ref('')

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [algRes, scenRes] = await Promise.all([
      api.listAlgorithms(),
      api.listScenarios()
    ])
    templates.value = algRes.templates || []
    scenarios.value = scenRes.scenarios || []
  } catch (err) {
    error.value = err.message || String(err)
  } finally {
    loading.value = false
  }
}

async function copyAsJson() {
  const payload = {
    templates: templates.value,
    scenarios: scenarios.value
  }
  try {
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
    error.value = ''
  } catch (err) {
    error.value = '复制失败: ' + (err.message || String(err))
  }
}

onMounted(refresh)
</script>

<style scoped>
.plugin-view {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.plugin-header h1 {
  margin: 0 0 0.5rem 0;
  font-size: 1.75rem;
}

.plugin-subtitle {
  color: var(--muted, #666);
  margin: 0 0 1rem 0;
  font-size: 0.95rem;
}

.plugin-subtitle code {
  background: var(--code-bg, #f4f4f5);
  padding: 0.05rem 0.3rem;
  border-radius: 4px;
  font-size: 0.9em;
}

.plugin-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.plugin-actions button {
  padding: 0.4rem 0.9rem;
  border-radius: 6px;
  border: 1px solid var(--border, #d4d4d8);
  background: var(--card-bg, #fff);
  cursor: pointer;
  font-size: 0.9rem;
}

.plugin-actions button.primary {
  background: var(--primary, #4f46e5);
  color: white;
  border-color: transparent;
}

.plugin-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.plugin-section {
  margin-bottom: 2rem;
}

.plugin-section h2 {
  font-size: 1.25rem;
  margin: 0 0 0.75rem 0;
}

.empty {
  color: var(--muted, #888);
  font-style: italic;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.card {
  border: 1px solid var(--border, #e4e4e7);
  border-radius: 8px;
  padding: 1rem;
  background: var(--card-bg, #fafafa);
}

.card.shadow {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

.badge {
  background: var(--badge-bg, #eef2ff);
  color: var(--badge-fg, #4f46e5);
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.card-name {
  font-size: 0.75rem;
  color: var(--muted, #888);
  font-family: monospace;
}

.card-body {
  font-size: 0.9rem;
  color: var(--body-fg, #444);
  margin: 0.5rem 0;
  line-height: 1.4;
}

.card-meta {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0 0;
  font-size: 0.85rem;
  color: var(--body-fg, #444);
}

.card-meta li {
  margin-bottom: 0.3rem;
}

.card-meta code {
  background: var(--code-bg, #f4f4f5);
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  font-size: 0.8em;
  margin-right: 0.2rem;
}

.tag {
  display: inline-block;
  background: var(--tag-bg, #ecfdf5);
  color: var(--tag-fg, #047857);
  padding: 0.05rem 0.4rem;
  border-radius: 3px;
  font-size: 0.7rem;
  margin-right: 0.2rem;
}

.card-source {
  font-size: 0.75rem;
  color: var(--muted, #888);
}

.error {
  color: #b91c1c;
  background: #fef2f2;
  padding: 1rem;
  border-radius: 6px;
}
</style>
