<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/api/client'

const router = useRouter()
const route = useRoute()

const llmReady = ref(false)
const llmText = ref('LLM checking')

onMounted(async () => {
  try {
    const data = await api.llmStatus()
    if (data.enabled) {
      llmReady.value = true
      llmText.value = `LLM ${data.model}`
    } else {
      llmText.value = 'LLM fallback'
    }
  } catch (_err) {
    llmText.value = 'LLM unknown'
  }
})

function goWorkspace() {
  router.push('/')
}

function goExperiment() {
  router.push('/experiment')
}
</script>

<template>
  <header class="app-header">
    <div class="brand" @click="goWorkspace">
      <div class="mark" aria-hidden="true"></div>
      <div>
        <h1>Energy Trading Lab</h1>
        <div class="subtitle">面向能源交易的科研仿真实验智能体</div>
      </div>
    </div>
    <div class="nav">
      <button
        class="nav-btn"
        :class="{ active: route.name === 'workspace' }"
        @click="goWorkspace"
      >
        工作空间
      </button>
      <button
        class="nav-btn"
        :class="{ active: route.name === 'experiment' }"
        @click="goExperiment"
      >
        实验工作台
      </button>
      <div class="status">
        <span class="dot" :class="{ ready: llmReady }"></span>
        <span>{{ llmText }}</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  min-height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 22px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 260px;
  cursor: pointer;
}

.mark {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background:
    linear-gradient(90deg, transparent 47%, rgba(255,255,255,0.82) 48%, rgba(255,255,255,0.82) 52%, transparent 53%),
    linear-gradient(0deg, transparent 47%, rgba(255,255,255,0.82) 48%, rgba(255,255,255,0.82) 52%, transparent 53%),
    var(--teal);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.38);
}

h1 {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0;
  line-height: 1.2;
}

.subtitle {
  color: var(--muted);
  font-size: 12px;
  margin-top: 3px;
}

.nav {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.nav-btn {
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: #344054;
  border-radius: 7px;
  font-weight: 600;
  font-size: 13px;
  transition: all 0.15s ease;
}

.nav-btn:hover {
  background: #eef2f6;
}

.nav-btn.active {
  background: var(--teal);
  color: #fff;
  border-color: var(--teal);
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: #344054;
  border-radius: 999px;
  padding: 8px 11px;
  font-size: 12px;
  white-space: nowrap;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--muted);
}

.dot.ready { background: var(--green); }
</style>
