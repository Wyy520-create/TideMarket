<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useUserStore } from '../store'
import { useToastStore } from '../toast'

const store = useUserStore()
const toasts = useToastStore()

const items = ref([])
const loading = ref(false)

const TYPE_ICONS = {
  'order.created': '🛒',
  'order.paid': '💰',
  'order.cancelled': '↩️',
  'order.expired': '⏰',
  'product.approved': '✅',
  'product.rejected': '❌',
}

async function load() {
  loading.value = true
  try {
    items.value = await api('/notifications')
    store.unread = items.value.filter((n) => !n.is_read).length
  } catch (e) {
    toasts.err('加载失败', e.message)
  } finally {
    loading.value = false
  }
}

async function readAll() {
  try {
    await api('/notifications/read_all', { method: 'POST' })
    store.unread = 0
    load()
  } catch (e) {
    toasts.err('操作失败', e.message)
  }
}

onMounted(load)
</script>

<template>
  <div style="display: flex; justify-content: space-between; align-items: center">
    <h2 class="page-title">通知中心</h2>
    <button v-if="items.some((n) => !n.is_read)" class="btn btn-sm" @click="readAll">全部已读</button>
  </div>

  <div v-if="loading" class="empty">加载中…</div>
  <div v-else-if="items.length === 0" class="empty">暂无通知。当有人拍下或支付你的商品时会第一时间通知你。</div>

  <div v-else class="note-list">
    <div v-for="n in items" :key="n.id" class="note-item" :class="{ unread: !n.is_read }">
      <span class="note-icon">{{ TYPE_ICONS[n.type] || '🔔' }}</span>
      <div class="note-main">
        <div class="note-title">{{ n.title }}</div>
        <div class="note-body">{{ n.body }}</div>
      </div>
      <span class="note-time">{{ new Date(n.created_at).toLocaleString('zh-CN') }}</span>
    </div>
  </div>
</template>
