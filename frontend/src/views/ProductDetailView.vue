<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, CATEGORY_NAMES, fen2yuan } from '../api'
import { useUserStore } from '../store'
import { useToastStore } from '../toast'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const toasts = useToastStore()

const product = ref(null)
const loading = ref(true)
const buying = ref(false)
const imgFailed = ref(false)

async function load() {
  loading.value = true
  try {
    product.value = await api(`/products/${route.params.id}`)
  } catch (e) {
    toasts.err('商品加载失败', e.message)
    router.push('/')
  } finally {
    loading.value = false
  }
}

function onImgError(e) {
  imgFailed.value = true
  e.target.style.display = 'none'
}

async function buy() {
  if (!store.isLogin) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  buying.value = true
  try {
    // 每次点击生成新的幂等键；网络重试/双击由后端唯一约束兜底
    const order = await api('/orders', {
      method: 'POST',
      body: { product_id: product.value.id, idempotency_key: crypto.randomUUID() },
    })
    toasts.ok('下单成功', '请在 15 分钟内完成支付，逾期订单自动关闭')
    router.push('/orders')
  } catch (e) {
    if (e.status === 409) {
      toasts.err('手慢了', e.message)
      load()
    } else {
      toasts.err('下单失败', e.message)
    }
  } finally {
    buying.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="empty">加载中…</div>
  <div v-else-if="product" class="detail">
    <div>
      <img
        v-if="product.images && product.images.length && !imgFailed"
        class="detail-img"
        :src="product.images[0]"
        :alt="product.title"
        @error="onImgError"
      />
      <div
        v-else
        class="detail-img"
        style="display: flex; align-items: center; justify-content: center; font-size: 90px; min-height: 320px; background: linear-gradient(135deg, #a5f3fc, #e0f2fe)"
      >🌊</div>
    </div>
    <div class="detail-info">
      <span class="badge info">{{ CATEGORY_NAMES[product.category] || '其他' }}</span>
      <h1>{{ product.title }}</h1>
      <div class="detail-price">¥{{ fen2yuan(product.price) }}</div>
      <div class="detail-meta">
        <span>库存：<b>{{ product.stock }}</b> 件</span>
        <span>卖家：{{ product.seller_name }}</span>
        <span>浏览 {{ product.views }} 次</span>
      </div>
      <div class="detail-desc">{{ product.description || '卖家很懒，什么都没有写。' }}</div>
      <button
        class="btn btn-primary"
        style="width: 100%; padding: 13px; font-size: 16px"
        :disabled="product.stock <= 0 || buying"
        @click="buy"
      >
        {{ product.stock <= 0 ? '已售罄' : buying ? '下单中…' : '立即购买' }}
      </button>
      <p class="muted" style="font-size: 12px; margin-top: 10px">
        下单后 15 分钟内未支付将自动取消并释放库存；热门商品先到先得。
      </p>
    </div>
  </div>
</template>
