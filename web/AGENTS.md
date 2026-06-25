# web/ — Vue 3 frontend + Tauri shell

> Read this before editing any file under `web/`.

## Layout

```
web/
├── index.html              # Vite entry
├── package.json
├── vite.config.js
├── src/
│   ├── main.js             # Vue app bootstrap
│   ├── App.vue
│   ├── style.css
│   ├── router/index.js
│   ├── api/client.js       # HTTP client, mirrors FastAPI endpoints
│   ├── components/
│   │   ├── AppHeader.vue
│   │   ├── MarkdownViewer.vue
│   │   └── MetricsChart.vue
│   ├── views/
│   │   ├── WorkspaceView.vue
│   │   ├── ExperimentView.vue
│   │   └── PluginView.vue
│   └── utils/
│       └── backend.js      # base URL resolution
└── src-tauri/              # Tauri desktop shell
    ├── tauri.conf.json
    ├── Cargo.toml
    ├── src/
    │   ├── main.rs
    │   └── lib.rs
    └── icons/
```

## Conventions

- Vue 3 SFC with `<script setup>` + Composition API. No Options API for new components.
- `ref` / `reactive` for state, `computed` for derived values, `onMounted` / `onUnmounted` for lifecycle.
- HTTP through `web/src/api/client.js` only. Do not call `fetch` from a component.
- Strings are Chinese (zh-CN) for the user-facing copy; English for the code comments. See `TRANSLATIONS.md`.
- Styling: scoped `<style scoped>` per component, CSS variables from `web/src/style.css` for the design tokens.

## Build

- `npm install` once.
- `npm run dev` — Vite dev server with HMR (used by the Tauri dev shell).
- `npm run build` — Vite production build; output goes to `web/dist/`. FastAPI serves it as static files.
- `npm run tauri:dev` — Tauri dev shell; uses the Vite dev server as the frontend.
- `npm run tauri:build` — Tauri production build; bundles the FastAPI backend + the Vue 3 frontend into a desktop app.

## Where things plug in

- New FastAPI endpoint → add a method to `web/src/api/client.js` and use it from the relevant view.
- New plugin surface (algorithms / scenarios) → consumed by `web/src/views/PluginView.vue`. The view polls `/api/plugins/algorithms` and `/api/plugins/scenarios`.
- New CLI subcommand → no web change required (the CLI is independent). However, the dual-track rule says the inverse is not true: any web change must be mirrored in the CLI.
