const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined
const API_BASE = isTauri ? 'http://localhost:8765/api' : '/api'

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.error || data.detail || `Request failed: ${res.status}`)
  }
  return data
}

export const api = {
  health: () => request('/health'),
  llmStatus: () => request('/llm-status'),
  listRuns: (limit = 30) => request(`/runs?limit=${limit}`),

  extractDocument: (payload) => request('/extract-document', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  createJob: (payload) => request('/jobs', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  getJob: (jobId) => request(`/jobs/${jobId}`),

  reproduce: (payload) => request('/reproduce', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  theory: (payload) => request('/theory', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  paper2code: (payload) => request('/paper2code', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  listProjects: () => request('/workspace/projects'),
  getProject: (runId) => request(`/workspace/projects/${runId}`),
  deleteProject: (runId) => request(`/workspace/projects/${runId}`, {
    method: 'DELETE'
  }),
  getProjectMetrics: (runId) => request(`/workspace/projects/${runId}/metrics`),
  getProjectTrace: (runId) => request(`/workspace/projects/${runId}/trace`),
  getProjectReport: (runId) => request(`/workspace/projects/${runId}/report`),
  getProjectArtifact: (runId, artifactName) => request(`/workspace/projects/${runId}/artifact/${artifactName}`)
}
