<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { api } from '@/api/client'

const router = useRouter()
const projects = ref([])
const loading = ref(true)
const error = ref('')

async function loadProjects() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.listProjects()
    projects.value = data.projects
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function formatDate(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function openProject(runId) {
  router.push(`/experiment/${runId}`)
}

async function deleteProject(runId, event) {
  event.stopPropagation()
  if (!confirm('确定要删除这个项目吗？此操作不可撤销。')) {
    return
  }
  try {
    await api.deleteProject(runId)
    projects.value = projects.value.filter(p => p.run_id !== runId)
  } catch (err) {
    alert('删除失败: ' + err.message)
  }
}

function newExperiment() {
  router.push('/experiment')
}

onMounted(() => {
  loadProjects()
})
</script>

<template>
  <div class="workspace-page">
    <AppHeader />
    
    <main class="workspace-main">
      <div class="page-header">
        <div>
          <h2>工作空间</h2>
          <p class="subtitle">管理和查看所有实验项目</p>
        </div>
        <button class="btn-primary" @click="newExperiment">
          + 新建实验
        </button>
      </div>

      <div v-if="loading" class="loading">
        加载中...
      </div>

      <div v-else-if="error" class="error">
        加载失败: {{ error }}
        <button @click="loadProjects">重试</button>
      </div>

      <div v-else-if="projects.length === 0" class="empty">
        <div class="empty-icon">📊</div>
        <h3>还没有实验项目</h3>
        <p>点击「新建实验」开始你的第一个能源交易仿真实验</p>
        <button class="btn-primary" @click="newExperiment">
          新建实验
        </button>
      </div>

      <div v-else class="project-grid">
        <div
          v-for="project in projects"
          :key="project.run_id"
          class="project-card"
          @click="openProject(project.run_id)"
        >
          <div class="project-header">
            <h3 class="project-title">{{ project.title || '未命名项目' }}</h3>
            <button
              class="delete-btn"
              @click="(e) => deleteProject(project.run_id, e)"
              title="删除项目"
            >
              ×
            </button>
          </div>
          
          <p class="project-problem" v-if="project.research_problem">
            {{ project.research_problem }}
          </p>

          <div class="project-meta">
            <span class="badge" :class="project.source_type">
              {{ project.source_type === 'paper' ? '论文复现' : project.source_type === 'theory' ? '理论实验' : project.source_type }}
            </span>
            <span class="meta-item">
              {{ project.strategy_count || 0 }} 种策略
            </span>
          </div>

          <div class="project-stats" v-if="project.best_strategy">
            <div class="stat">
              <span class="stat-label">最优策略</span>
              <span class="stat-value">{{ project.best_strategy }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">最优成本</span>
              <span class="stat-value">{{ project.best_cost?.toFixed(2) }}</span>
            </div>
          </div>

          <div class="project-footer">
            <span class="artifact-count">
              {{ project.artifact_count || 0 }} 个文件
            </span>
            <span class="project-date">
              {{ formatDate(project.created_at) }}
            </span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.workspace-page {
  min-height: 100vh;
}

.workspace-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: var(--ink);
}

.subtitle {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.btn-primary {
  height: 40px;
  padding: 0 20px;
  border: 0;
  border-radius: 7px;
  background: var(--teal);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-primary:hover {
  background: #0f665c;
}

.loading, .error, .empty {
  text-align: center;
  padding: 60px 20px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  color: var(--muted);
}

.error button {
  display: block;
  margin: 12px auto 0;
  padding: 8px 16px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  border-radius: 6px;
  cursor: pointer;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty h3 {
  margin: 0 0 8px;
  color: var(--ink);
}

.empty p {
  margin: 0 0 20px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.project-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.project-card:hover {
  border-color: var(--teal);
  box-shadow: 0 8px 24px rgba(18, 119, 109, 0.12);
  transform: translateY(-2px);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.project-title {
  margin: 0;
  font-size: 16px;
  color: var(--ink);
  line-height: 1.4;
  flex: 1;
}

.delete-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: var(--muted);
  border-radius: 6px;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.delete-btn:hover {
  background: var(--red);
  color: #fff;
  border-color: var(--red);
}

.project-problem {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.badge.paper {
  background: #e8f3f1;
  color: var(--teal);
}

.badge.theory {
  background: #eff6ff;
  color: var(--blue);
}

.meta-item {
  font-size: 12px;
  color: var(--muted);
}

.project-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  margin-bottom: 12px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
}

.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
}
</style>
