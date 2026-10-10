<script setup>
import { onMounted, ref } from 'vue'
import { api, fen2yuan } from '../api'
import { useToastStore } from '../toast'

const toasts = useToastStore()

const stats = ref(null)
const queue = ref([])
const users = ref([])
const loading = ref(false)
const busyId = ref(null)

async function loadStats() {
  stats.value = await api('/admin/stats')
}

async function loadQueue() {
  queue.value = await api('/admin/products?pending_only=true')
}

async function loadUsers() {
  users.value = await api('/admin/users')
}

async function load() {
  loading.value = true
  try {
    await Promise.all([loadStats(), loadQueue(), loadUsers()])
  } catch (e) {
    toasts.err('加载失败', e.message)
  } finally {
    loading.value = false
  }
}

async function review(pid, action) {
  busyId.value = pid
  try {
    await api(`/admin/products/${pid}/${action}`, { method: 'POST' })
    toasts.ok(action === 'approve' ? '已通过上架' : '已拒绝', '卖家将收到实时通知')
    await Promise.all([loadStats(), loadQueue()])
  } catch (e) {
    toasts.err('操作失败', e.message)
  } finally {
    busyId.value = null
  }
}

async function toggleRole(u) {
  const next = u.role === 'admin' ? 'user' : 'admin'
  try {
    await api(`/admin/users/${u.id}/role`, { method: 'PATCH', body: { role: next } })
    toasts.ok('角色已更新', `${u.username} 现在是${next === 'admin' ? '管理员' : '普通用户'}`)
    await Promise.all([loadStats(), loadUsers()])
  } catch (e) {
    toasts.err('操作失败', e.message)
  }
}

onMounted(load)
</script>

<template>
  <h2 class="page-title">管理后台</h2>

  <div v-if="loading && !stats" class="empty">加载中…</div>

  <template v-else>
    <div class="stats-row">
      <div class="stat-card"><div class="stat-num">{{ stats?.users ?? '-' }}</div><div class="stat-label">注册用户</div></div>
      <div class="stat-card"><div class="stat-num">{{ stats?.products ?? '-' }}</div><div class="stat-label">商品总数</div></div>
      <div class="stat-card"><div class="stat-num">{{ stats?.pending_products ?? '-' }}</div><div class="stat-label">待审核</div></div>
      <div class="stat-card"><div class="stat-num">{{ stats?.orders ?? '-' }}</div><div class="stat-label">订单总数</div></div>
      <div class="stat-card"><div class="stat-num">{{ stats?.paid_orders ?? '-' }}</div><div class="stat-label">已支付订单</div></div>
    </div>

    <div class="table-card">
      <h3>商品审核队列（{{ queue.length }} 件待审核）</h3>
      <div v-if="queue.length === 0" class="empty">队列已清空，所有商品都已处理 👏</div>
      <table v-else>
        <thead>
          <tr><th>图片</th><th>标题</th><th>卖家</th><th>价格</th><th>库存</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in queue" :key="p.id">
            <td>
              <img v-if="p.images?.length" :src="p.images[0]" alt="商品图" />
              <span v-else class="muted">无图</span>
            </td>
            <td>{{ p.title }}</td>
            <td>{{ p.seller_name }}</td>
            <td class="price">¥{{ fen2yuan(p.price) }}</td>
            <td>{{ p.stock }}</td>
            <td>
              <div style="display: flex; gap: 6px">
                <button class="btn btn-primary btn-sm" :disabled="busyId === p.id" @click="review(p.id, 'approve')">通过</button>
                <button class="btn btn-danger btn-sm" :disabled="busyId === p.id" @click="review(p.id, 'reject')">拒绝</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="table-card">
      <h3>用户与角色（RBAC）</h3>
      <table>
        <thead>
          <tr><th>ID</th><th>用户名</th><th>角色</th><th>发布商品</th><th>购买订单</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td><span class="badge" :class="u.role === 'admin' ? 'info' : 'muted'">{{ u.role === 'admin' ? '管理员' : '普通用户' }}</span></td>
            <td>{{ u.product_count }}</td>
            <td>{{ u.order_count }}</td>
            <td>
              <button class="btn btn-sm" :disabled="u.role === 'admin'" @click="toggleRole(u)">设为管理员</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>
