<script setup>
import { onMounted, ref } from 'vue'
import { api, fen2yuan, ORDER_STATUS } from '../api'
import { useToastStore } from '../toast'

const toasts = useToastStore()

const role = ref('buyer')
const orders = ref([])
const loading = ref(false)

const payTarget = ref(null)
const paying = ref(false)
const cancelTarget = ref(null)
const cancelling = ref(false)

const PAY_MINUTES = 15

async function load() {
  loading.value = true
  try {
    orders.value = await api(`/orders/mine?role=${role.value}`)
  } catch (e) {
    toasts.err('加载失败', e.message)
  } finally {
    loading.value = false
  }
}

function switchRole(r) {
  role.value = r
  load()
}

function payDeadline(createdAt) {
  const d = new Date(new Date(createdAt).getTime() + PAY_MINUTES * 60000)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function confirmPay() {
  paying.value = true
  try {
    // 模拟支付回调：同一订单每次点击生成不同回调 key，重复回调由后端去重
    await api(`/orders/${payTarget.value.id}/pay?key=${crypto.randomUUID()}`, { method: 'POST' })
    toasts.ok('支付成功', '卖家将实时收到收款通知')
    payTarget.value = null
    load()
  } catch (e) {
    toasts.err('支付失败', e.message)
    payTarget.value = null
  } finally {
    paying.value = false
  }
}

async function confirmCancel() {
  cancelling.value = true
  try {
    await api(`/orders/${cancelTarget.value.id}/cancel`, { method: 'POST' })
    toasts.ok('订单已取消', '库存已实时回补，其他买家可以继续抢购')
    cancelTarget.value = null
    load()
  } catch (e) {
    toasts.err('取消失败', e.message)
    cancelTarget.value = null
  } finally {
    cancelling.value = false
  }
}

onMounted(load)
</script>

<template>
  <h2 class="page-title">我的订单</h2>
  <div class="tabs">
    <button class="btn" :class="{ active: role === 'buyer' }" @click="switchRole('buyer')">我买到的</button>
    <button class="btn" :class="{ active: role === 'seller' }" @click="switchRole('seller')">我卖出的</button>
  </div>

  <div v-if="loading" class="empty">加载中…</div>
  <div v-else-if="orders.length === 0" class="empty">
    {{ role === 'buyer' ? '还没有买到任何东西，去首页逛逛吧' : '还没有卖出商品，去发布一件闲置吧' }}
  </div>

  <div v-else class="order-list">
    <div v-for="o in orders" :key="o.id" class="order-item">
      <img v-if="o.product_image" class="order-img" :src="o.product_image" alt="商品图" />
      <div v-else class="order-img" style="display: flex; align-items: center; justify-content: center; font-size: 26px; background: linear-gradient(135deg, #a5f3fc, #e0f2fe)">🌊</div>
      <div class="order-main">
        <div class="order-title">{{ o.product_title }}</div>
        <div class="order-sub">
          订单号 {{ o.id }} · {{ new Date(o.created_at).toLocaleString('zh-CN') }}
        </div>
        <div class="order-sub" v-if="o.status === 'pending'">
          请在今天 {{ payDeadline(o.created_at) }} 前完成支付
        </div>
      </div>
      <div class="order-side">
        <span class="price">¥{{ fen2yuan(o.amount) }}</span>
        <span class="badge" :class="ORDER_STATUS[o.status]?.cls">{{ ORDER_STATUS[o.status]?.text }}</span>
        <div v-if="role === 'buyer' && o.status === 'pending'" class="order-actions">
          <button class="btn btn-primary btn-sm" @click="payTarget = o">去支付</button>
          <button class="btn btn-danger btn-sm" @click="cancelTarget = o">取消</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 模拟支付弹窗 -->
  <div v-if="payTarget" class="modal-mask" @click.self="payTarget = null">
    <div class="modal">
      <h3>🧾 模拟收银台</h3>
      <p>
        订单：{{ payTarget.product_title }}<br />
        应付金额：<span class="price" style="font-size: 18px">¥{{ fen2yuan(payTarget.amount) }}</span>
      </p>
      <p class="muted" style="font-size: 12px">点击确认即模拟一次支付回调；重复回调由幂等去重表保证只入账一次。</p>
      <div class="modal-actions">
        <button class="btn" @click="payTarget = null">再想想</button>
        <button class="btn btn-primary" :disabled="paying" @click="confirmPay">{{ paying ? '支付中…' : '确认支付' }}</button>
      </div>
    </div>
  </div>

  <!-- 取消确认弹窗 -->
  <div v-if="cancelTarget" class="modal-mask" @click.self="cancelTarget = null">
    <div class="modal">
      <h3>取消订单？</h3>
      <p>取消后库存立即释放，该操作不可撤销。</p>
      <div class="modal-actions">
        <button class="btn" @click="cancelTarget = null">保留订单</button>
        <button class="btn btn-danger" :disabled="cancelling" @click="confirmCancel">{{ cancelling ? '取消中…' : '确认取消' }}</button>
      </div>
    </div>
  </div>
</template>
