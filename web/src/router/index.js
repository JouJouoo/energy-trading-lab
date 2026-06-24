import { createRouter, createWebHistory } from 'vue-router'
import WorkspaceView from '../views/WorkspaceView.vue'
import ExperimentView from '../views/ExperimentView.vue'

const routes = [
  {
    path: '/',
    name: 'workspace',
    component: WorkspaceView
  },
  {
    path: '/experiment/:runId?',
    name: 'experiment',
    component: ExperimentView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
