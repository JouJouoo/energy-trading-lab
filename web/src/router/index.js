import { createRouter, createWebHistory } from 'vue-router'
import WorkspaceView from '../views/WorkspaceView.vue'
import ExperimentView from '../views/ExperimentView.vue'
import PluginView from '../views/PluginView.vue'

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
  },
  {
    path: '/plugins',
    name: 'plugins',
    component: PluginView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
