<script setup>import { computed } from 'vue';
import { marked } from 'marked';
const props = defineProps({
 content: {
 type: String,
 default: ''
 },
 maxLength: {
 type: Number,
 default: null
 }
});
const renderedContent = computed(() => {
 let content = props.content || '';
 if (props.maxLength && content.length > props.maxLength) {
 content = content.substring(0, props.maxLength) + '...';
 }
 const html = marked(content, {
 gfm: true,
 breaks: true
 });
 return html;
});
</script>

<template>
  <div class="markdown-viewer" v-html="renderedContent"></div>
</template>

<style scoped>
.markdown-viewer {
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink);
}

.markdown-viewer :deep(h1) {
  font-size: 22px;
  font-weight: 800;
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}

.markdown-viewer :deep(h2) {
  font-size: 18px;
  font-weight: 700;
  margin: 20px 0 10px;
}

.markdown-viewer :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 16px 0 8px;
}

.markdown-viewer :deep(p) {
  margin: 10px 0;
}

.markdown-viewer :deep(ul),
.markdown-viewer :deep(ol) {
  padding-left: 24px;
  margin: 10px 0;
}

.markdown-viewer :deep(li) {
  margin: 6px 0;
}

.markdown-viewer :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: ui-monospace, monospace;
}

.markdown-viewer :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-viewer :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-viewer :deep(blockquote) {
  border-left: 4px solid var(--teal);
  padding-left: 14px;
  margin: 12px 0;
  color: var(--muted);
  font-style: italic;
}

.markdown-viewer :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

.markdown-viewer :deep(th),
.markdown-viewer :deep(td) {
  border: 1px solid var(--line);
  padding: 8px 12px;
  text-align: left;
}

.markdown-viewer :deep(th) {
  background: #f8fafc;
  font-weight: 600;
}

.markdown-viewer :deep(a) {
  color: var(--teal);
  text-decoration: underline;
}

.markdown-viewer :deep(hr) {
  border: none;
  border-top: 1px solid var(--line);
  margin: 20px 0;
}
</style>
