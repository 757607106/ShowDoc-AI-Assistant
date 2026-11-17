<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { getDown } from '@/utils/request'
import { attachmentPath, type KnowledgeAttachment } from '@/utils/contextdbResources'

const props = defineProps<{ attachment: KnowledgeAttachment; kbId?: string; label?: string }>()
const root = ref<HTMLElement | null>(null)
const url = ref(''), error = ref(''), loading = ref(false)
let generation = 0, observer: IntersectionObserver | undefined

function clear() {
  generation++
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''; error.value = ''; loading.value = false
}
async function load() {
  if (loading.value || url.value) return
  const token = generation
  loading.value = true; error.value = ''
  try {
    const blob = props.attachment.source_blob || await getDown(attachmentPath(props.attachment, props.kbId))
    if (token !== generation) return
    if (!blob.size) throw new Error('附件内容为空')
    url.value = URL.createObjectURL(blob)
  } catch (e: any) {
    if (token === generation) error.value = e?.message || '附件加载失败'
  } finally { if (token === generation) loading.value = false }
}
function observe() {
  observer?.disconnect()
  if (props.attachment.type !== 'image') return
  if (!root.value || typeof IntersectionObserver === 'undefined') { void load(); return }
  observer = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) { observer?.disconnect(); void load() }
  }, { rootMargin: '150px' })
  observer.observe(root.value)
}
watch([() => JSON.stringify([props.kbId, props.attachment.document_id, props.attachment.embedded_key || attachmentPath(props.attachment, props.kbId)]), () => props.attachment.source_blob], () => { clear(); observe() })
onMounted(observe)
onUnmounted(() => { observer?.disconnect(); clear() })
</script>

<template>
  <figure ref="root" class="source-attachment">
    <t-loading v-if="loading" text="正在读取来源附件" />
    <template v-if="url">
      <img v-if="attachment.type === 'image'" :src="url" :alt="label || '来源图片'" loading="lazy" @error="error='图片无法显示，请下载原件核对'" />
      <audio v-else-if="attachment.type === 'audio'" :src="url" controls preload="metadata" :aria-label="label || '来源音频'" />
      <video v-else-if="attachment.type === 'video'" :src="url" controls preload="metadata" :aria-label="label || '来源视频'" />
    </template>
    <t-button v-else-if="!loading && !error" size="small" variant="outline" @click="load">{{ attachment.type === 'image' ? '读取图片' : '读取音视频附件' }}</t-button>
    <p v-if="error" role="alert">{{ error }} <t-button size="small" variant="text" @click="clear();load()">重试</t-button></p>
    <figcaption v-if="label">{{ label }}</figcaption>
  </figure>
</template>

<style scoped>
.source-attachment { margin: 12px 0; min-height: 40px; }
.source-attachment img, .source-attachment video { display: block; max-width: 100%; max-height: 480px; object-fit: contain; border-radius: var(--app-radius-xs); }
.source-attachment audio { max-width: 100%; }
.source-attachment figcaption { margin-top: 6px; color: var(--td-text-color-secondary); font-size: 12px; }
.source-attachment p { color: var(--td-error-color); }
</style>
