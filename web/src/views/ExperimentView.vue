<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import MarkdownViewer from '@/components/MarkdownViewer.vue'
import MetricsChart from '@/components/MetricsChart.vue'
import { api } from '@/api/client'

const route = useRoute()
const runId = computed(() => route.params.runId)

const mode = ref('reproduce')
const inputText = ref('')
const gridCase = ref('ieee33')
const experimentDepth = ref('quick')
const llmProvider = ref('openai')
const llmModel = ref('gpt-4o-mini')
const llmBaseUrl = ref('https://api.openai.com/v1')
const llmApiKey = ref('')
const llmDisabled = ref(false)
const statusText = ref('Ready')
const statusKind = ref('ready')

const jobId = ref('')
const currentStep = ref('Idle')
const currentSummary = ref('')
const progressPercent = ref(0)
const events = ref([])
const result = ref(null)
const running = ref(false)

const charCount = computed(() => inputText.value.length)

const SAMPLE_PAPER = `# Network-aware multi-agent reinforcement learning for P2P energy trading

This study investigates peer-to-peer energy trading among prosumers in an IEEE 33-bus distribution network. The market uses double auction clearing and compares no trading, rule-based bidding, optimization clearing, and multi-agent reinforcement learning. Agent states include PV generation, load, battery SOC, time-of-use price, and voltage. Actions include buy/sell/hold, bid quantity, bid price, and storage dispatch. The reward minimizes energy cost and carbon emissions while penalizing voltage violations and network loss.`

const SAMPLE_THEORY = `我提出一种面向 P2P 能源交易的低碳电压感知奖励机制。在 IEEE 33/69 节点配电网中，prosumer 不仅根据本地光伏、负荷、储能 SOC 和电价报价，还需要感知节点电压风险和实时碳强度。理论预期是：相比传统双边拍卖和普通强化学习，加入电压越限惩罚与碳排惩罚后，可以在保持较高 P2P 交易量的同时降低网损、碳排和越限次数。`

function setMode(next) {
  mode.value = next
}

function loadSample() {
  if (mode.value === 'reproduce') {
    inputText.value = SAMPLE_PAPER
  } else {
    inputText.value = SAMPLE_THEORY
  }
}

const uploading = ref(false)
const uploadFile = ref(null)
const uploadInfo = ref(null)
const uploadError = ref('')
const fileInput = ref(null)

function triggerFilePicker() {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

function onFileSelected(event) {
  const file = event.target.files[0]
  if (file) {
    handleFileUpload(file)
  }
  if (event.target) {
    event.target.value = ''
  }
}

function onDrop(event) {
  event.preventDefault()
  const file = event.dataTransfer.files[0]
  if (file) {
    handleFileUpload(file)
  }
}

function onDragOver(event) {
  event.preventDefault()
}

async function handleFileUpload(file) {
  if (uploading.value) return

  uploading.value = true
  uploadError.value = ''
  uploadInfo.value = null
  uploadFile.value = file

  try {
    const result = await api.uploadDocument(file)
    inputText.value = result.text
    uploadInfo.value = {
      filename: result.filename,
      chars: result.chars,
      method: result.method
    }
  } catch (err) {
    uploadError.value = err.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

function getLLMConfig() {
  return {
    provider: llmProvider.value,
    base_url: llmBaseUrl.value,
    model: llmModel.value,
    api_key: llmApiKey.value,
    timeout_sec: 30,
    temperature: 0.1,
    max_tokens: 2500,
    disabled: llmDisabled.value
  }
}

async function runExperiment() {
  if (running.value) return
  
  running.value = true
  statusKind.value = 'busy'
  statusText.value = 'Running'
  events.value = []
  result.value = null
  progressPercent.value = 4
  currentStep.value = 'Starting'
  currentSummary.value = '正在创建后台任务...'
  
  try {
    const job = await api.createJob({
      mode: mode.value,
      text: inputText.value,
      grid_case: gridCase.value,
      experiment_depth: experimentDepth.value,
      llm_config: getLLMConfig()
    })
    
    jobId.value = job.job_id
    pollJob(job.job_id)
  } catch (err) {
    statusKind.value = 'error'
    statusText.value = 'Error'
    currentSummary.value = err.message
    running.value = false
  }
}

let pollTimer = null

function pollJob(id) {
  if (!id) return
  
  async function doPoll() {
    try {
      const job = await api.getJob(id)
      
      currentStep.value = job.current_step || job.status
      currentSummary.value = job.current_summary || ''
      events.value = job.events || []
      
      const eventCount = events.value.length
      if (job.status === 'completed') {
        progressPercent.value = 100
      } else {
        progressPercent.value = Math.min(92, 8 + eventCount * 7)
      }
      
      if (job.status === 'completed') {
        result.value = job.result
        statusKind.value = 'ready'
        statusText.value = 'Ready'
        running.value = false
        return
      }
      
      if (job.status === 'failed') {
        statusKind.value = 'error'
        statusText.value = 'Error'
        currentSummary.value = job.error || 'Job failed'
        running.value = false
        return
      }
      
      pollTimer = setTimeout(doPoll, 500)
    } catch (err) {
      statusKind.value = 'error'
      statusText.value = 'Error'
      currentSummary.value = err.message
      running.value = false
    }
  }
  
  doPoll()
}

function formatNumber(value, digits = 2) {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(digits) : '-'
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[char]))
}

onMounted(() => {
  if (runId.value) {
    loadProject(runId.value)
  }
})

onUnmounted(() => {
  if (pollTimer) {
    clearTimeout(pollTimer)
  }
})

async function loadProject(id) {
  try {
    const project = await api.getProject(id)
    if (project) {
      statusKind.value = 'ready'
      statusText.value = 'Completed'
      const metrics = await api.getProjectMetrics(id)
      const trace = await api.getProjectTrace(id)
      const report = await api.getProjectReport(id)
      
      result.value = {
        run_id: project.run_id,
        run_dir: project.run_dir,
        metrics: metrics.metrics,
        trace: trace.trace,
        report_preview: report.report
      }
    }
  } catch (err) {
    console.error('Failed to load project:', err)
  }
}
</script>

<template>
  <div class="experiment-page">
    <AppHeader />
    
    <main class="experiment-main">
      <section class="control-panel">
        <div class="panel-title">
          <h2>Experiment Brief</h2>
          <span class="hint">{{ charCount }} chars</span>
        </div>

        <label>工作流</label>
        <div class="segmented" role="tablist">
          <button :class="{ active: mode === 'reproduce' }" type="button" @click="setMode('reproduce')">
            Paper
          </button>
          <button :class="{ active: mode === 'theory' }" type="button" @click="setMode('theory')">
            Theory
          </button>
        </div>

        <label>实验深度</label>
        <select v-model="experimentDepth">
          <option value="research">Research · 7 days · 3000 episodes</option>
          <option value="quick">Demo · 48 hours · 100 episodes</option>
          <option value="deep">Deep · 14 days · 12000 episodes</option>
        </select>
        <div class="hint" style="margin-top:6px;">
          Research/Deep 会真实训练 RL 策略并输出训练曲线，运行时间会明显更长。
        </div>

        <label>电网案例</label>
        <select v-model="gridCase">
          <option value="ieee33">IEEE 33</option>
          <option value="ieee69">IEEE 69</option>
        </select>

        <label>大模型 API</label>
        <div class="llm-panel">
          <div class="form-grid">
            <div>
              <span class="field-label">Provider</span>
              <select v-model="llmProvider">
                <option value="openai">OpenAI</option>
                <option value="deepseek">DeepSeek</option>
                <option value="qwen">Qwen / DashScope</option>
                <option value="kimi">Kimi / Moonshot</option>
                <option value="custom">Custom compatible</option>
              </select>
            </div>
            <div>
              <span class="field-label">Model</span>
              <input v-model="llmModel" autocomplete="off" />
            </div>
          </div>
          <div class="form-grid full">
            <div>
              <span class="field-label">Base URL</span>
              <input v-model="llmBaseUrl" autocomplete="off" />
            </div>
            <div>
              <span class="field-label">API Key</span>
              <input v-model="llmApiKey" type="password" placeholder="sk-..." autocomplete="off" />
            </div>
          </div>
          <div class="toggle-row">
            <span class="hint">未填 API Key 时会使用后端环境变量。</span>
            <label style="margin:0;display:flex;align-items:center;gap:7px;font-size:12px;">
              <input type="checkbox" v-model="llmDisabled" />
              Disable
            </label>
          </div>
        </div>

        <label for="input">{{ mode === 'reproduce' ? '论文文本' : '中文理论草稿' }}</label>

        <div class="upload-area"
             :class="{ dragging: false, hasFile: uploadInfo }"
             @drop="onDrop"
             @dragover="onDragOver">
          <input
            ref="fileInput"
            type="file"
            accept=".pdf,.txt,.md,.markdown,.rst,.tex,.csv"
            @change="onFileSelected"
            style="display: none"
          />
          <div class="upload-content" v-if="!uploading && !uploadInfo">
            <button type="button" class="upload-btn" @click="triggerFilePicker">
              📄 上传论文文件
            </button>
            <span class="upload-hint">支持 PDF / TXT / Markdown · 拖拽文件到此处</span>
          </div>
          <div class="upload-content" v-else-if="uploading">
            <div class="upload-spinner">⏳</div>
            <span>正在解析 {{ uploadFile?.name }}...</span>
          </div>
          <div class="upload-success" v-else-if="uploadInfo">
            <div class="upload-filename">✅ {{ uploadInfo.filename }}</div>
            <div class="upload-meta">
              提取了 {{ uploadInfo.chars }} 个字符 · 方法: {{ uploadInfo.method }}
            </div>
            <button type="button" class="reupload-btn" @click="triggerFilePicker">重新上传</button>
          </div>
          <div class="upload-error" v-if="uploadError">
            ❌ {{ uploadError }}
          </div>
        </div>

        <textarea v-model="inputText" placeholder="或在此处直接粘贴论文文本..."></textarea>

        <div class="button-row">
          <button class="primary" type="button" @click="runExperiment" :disabled="running">
            {{ running ? 'Running...' : 'Run Agent' }}
          </button>
          <button class="secondary" type="button" @click="loadSample">
            Load Sample
          </button>
        </div>
      </section>

      <div class="dashboard">
        <section class="hero-panel">
          <div>
            <div class="summary-title">
              {{ result?.run_id ? result.run_id : 'Research workspace' }}
            </div>
            <div class="summary-copy">
              {{ currentSummary || 'Run a paper reproduction or theory experiment to generate model specs, strategy classification, IEEE feeder validation, and a research report.' }}
            </div>
          </div>
          <div class="status-box">
            <div>
              <strong>状态</strong>
              <div class="status-text">{{ statusText }}</div>
            </div>
            <div class="hint">
              {{ progressPercent }}%
            </div>
          </div>
        </section>

        <section class="live-panel">
          <div class="live-header">
            <div>
              <div class="live-step">{{ currentStep }}</div>
              <div class="live-summary">{{ currentSummary }}</div>
            </div>
            <span class="hint">{{ events.length }} events</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
        </section>

        <section v-if="result?.metrics" class="metrics-grid">
          <div class="metric">
            <span>Best Strategy</span>
            <strong>{{ result.metrics.reduce((w, r) => !w || Number(r.total_cost) < Number(w.total_cost) ? r : w, null)?.strategy || '-' }}</strong>
            <small>lowest cost</small>
          </div>
          <div class="metric">
            <span>Strategies</span>
            <strong>{{ result.metrics.length }}</strong>
            <small>compared</small>
          </div>
          <div class="metric">
            <span>P2P Volume</span>
            <strong>{{ formatNumber(Math.max(...result.metrics.map(m => Number(m.p2p_volume_kwh) || 0)), 1) }}</strong>
            <small>kWh max</small>
          </div>
          <div class="metric">
            <span>Run ID</span>
            <strong style="font-size:14px;">{{ result.run_id || '-' }}</strong>
            <small>experiment</small>
          </div>
        </section>

        <section v-if="result?.metrics" class="panel section">
          <div class="panel-title">
            <h2>Strategy Comparison</h2>
            <span class="hint">{{ result.metrics.length }} strategies</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Cost</th>
                  <th>P2P kWh</th>
                  <th>Carbon kg</th>
                  <th>Min V</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in result.metrics" :key="row.strategy">
                  <td><strong>{{ row.strategy }}</strong></td>
                  <td>{{ formatNumber(row.total_cost, 3) }}</td>
                  <td>{{ formatNumber(row.p2p_volume_kwh, 2) }}</td>
                  <td>{{ formatNumber(row.carbon_kg, 2) }}</td>
                  <td>{{ formatNumber(row.grid_validation?.min_voltage_pu, 4) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-if="result?.trace" class="panel section">
          <div class="panel-title">
            <h2>Agent Trace</h2>
            <span class="hint">{{ result.trace.length }} steps</span>
          </div>
          <div class="trace">
            <div v-for="(row, index) in result.trace.slice(-10)" :key="index" class="trace-item">
              <div class="trace-index">{{ index + 1 }}</div>
              <div class="trace-body">
                <strong>{{ row.step || row.name }}</strong>
                <span>{{ row.summary || '' }}</span>
              </div>
            </div>
          </div>
        </section>

        <section v-if="result?.metrics" class="panel section">
          <div class="panel-title">
            <h2>Visual Analysis</h2>
            <span class="hint">Charts</span>
          </div>
          <MetricsChart :metrics="result.metrics" />
        </section>

        <section v-if="result?.report_preview" class="panel section">
          <div class="panel-title">
            <h2>Report Preview</h2>
            <span class="hint">Markdown</span>
          </div>
          <MarkdownViewer :content="result.report_preview" :max-length="4200" />
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.experiment-page {
  min-height: 100vh;
}

.experiment-main {
  display: grid;
  grid-template-columns: 390px minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
  max-width: 1500px;
  margin: 0 auto;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.control-panel {
  padding: 16px;
  align-self: start;
  position: sticky;
  top: 88px;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.panel-title h2 {
  margin: 0;
  font-size: 14px;
  letter-spacing: 0;
}

.hint {
  color: var(--muted);
  font-size: 12px;
}

label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #344054;
  margin: 14px 0 6px;
}

textarea, select, input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  outline: none;
}

select {
  height: 38px;
  padding: 0 10px;
}

input {
  height: 38px;
  padding: 0 10px;
}

textarea {
  min-height: 200px;
  resize: vertical;
  line-height: 1.52;
  padding: 11px;
  font-size: 13px;
}

textarea:focus, select:focus, input:focus {
  border-color: var(--teal);
  box-shadow: 0 0 0 3px rgba(18, 119, 109, 0.12);
}

.upload-area {
  border: 2px dashed var(--line);
  border-radius: 8px;
  padding: 18px;
  margin-bottom: 10px;
  background: #fafbfd;
  text-align: center;
  transition: all 0.18s ease;
}

.upload-area.dragging,
.upload-area:hover {
  border-color: var(--teal);
  background: rgba(18, 119, 109, 0.04);
}

.upload-area.hasFile {
  border-style: solid;
  background: #f0f9f7;
  border-color: var(--teal);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-btn {
  background: var(--teal);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.upload-btn:hover {
  background: #0e5f55;
}

.upload-hint {
  font-size: 12px;
  color: var(--muted);
}

.upload-spinner {
  font-size: 20px;
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.upload-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.upload-filename {
  font-size: 13px;
  font-weight: 600;
  color: var(--teal);
}

.upload-meta {
  font-size: 12px;
  color: var(--muted);
}

.reupload-btn {
  background: transparent;
  color: var(--teal);
  border: 1px solid var(--teal);
  border-radius: 5px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  margin-top: 4px;
}

.reupload-btn:hover {
  background: var(--teal);
  color: #fff;
}

.upload-error {
  margin-top: 8px;
  font-size: 12px;
  color: #c0392b;
}

.llm-panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcff;
  padding: 11px;
  display: grid;
  gap: 9px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.form-grid.full {
  grid-template-columns: 1fr;
}

.field-label {
  display: block;
  color: #475467;
  font-size: 11px;
  font-weight: 750;
  margin: 0 0 5px;
}

.segmented {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  background: #eef2f6;
  padding: 4px;
  border-radius: 8px;
  border: 1px solid var(--line);
}

.segmented button {
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #475467;
  font-weight: 700;
  height: 34px;
  cursor: pointer;
}

.segmented button.active {
  background: #fff;
  color: var(--teal);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--line);
  padding-top: 8px;
}

.toggle-row input {
  width: 18px;
  height: 18px;
  padding: 0;
}

.button-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

button.primary, button.secondary {
  appearance: none;
  height: 40px;
  border: 0;
  border-radius: 7px;
  font-weight: 760;
  cursor: pointer;
}

button.primary {
  color: #fff;
  background: var(--teal);
}

button.secondary {
  color: #344054;
  background: #eef2f6;
  border: 1px solid var(--line);
}

button:disabled {
  opacity: 0.62;
  cursor: wait;
}

.dashboard {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.hero-panel {
  padding: 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 200px;
  gap: 18px;
  align-items: stretch;
}

.summary-title {
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 6px;
}

.summary-copy {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
  max-width: 780px;
}

.status-box {
  background: #102033;
  color: #d7e5f7;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  min-height: 112px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.status-box strong {
  color: #fff;
  font-size: 13px;
}

.status-text {
  margin-top: 6px;
  font-size: 14px;
  font-weight: 600;
}

.grid {
  display: grid;
  gap: 14px;
}

.metrics-grid {
  grid-template-columns: repeat(4, minmax(140px, 1fr));
}

.live-panel {
  padding: 14px 16px;
}

.live-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.live-step {
  font-size: 14px;
  font-weight: 800;
}

.live-summary {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
  margin-top: 4px;
}

.progress-track {
  height: 8px;
  background: #e5ebf3;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  width: 0%;
  height: 100%;
  background: var(--teal);
  border-radius: 999px;
  transition: width 0.2s ease;
}

.metric {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 13px;
  min-height: 88px;
}

.metric span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
}

.metric strong {
  display: block;
  font-size: 24px;
  margin: 7px 0 2px;
  letter-spacing: 0;
}

.metric small {
  color: #475467;
  font-size: 12px;
}

.section {
  padding: 15px;
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 500px;
  font-size: 12px;
}

th, td {
  padding: 10px 11px;
  text-align: left;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}

th {
  color: #344054;
  background: #f8fafc;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

tr:last-child td { border-bottom: 0; }

.trace {
  display: grid;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.trace-item {
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 9px;
  align-items: start;
}

.trace-index {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #e8f3f1;
  color: var(--teal);
  font-size: 11px;
  font-weight: 800;
}

.trace-body {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 10px;
  background: #fff;
}

.trace-body strong {
  display: block;
  font-size: 12px;
  margin-bottom: 3px;
}

.trace-body span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
}

@media (max-width: 1100px) {
  .experiment-main { grid-template-columns: 1fr; }
  .control-panel { position: static; }
  .hero-panel { grid-template-columns: 1fr; }
}

@media (max-width: 720px) {
  .experiment-main { padding: 12px; }
  .metrics-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .button-row { grid-template-columns: 1fr; }
}
</style>
