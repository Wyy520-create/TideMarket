<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, CATEGORY_NAMES } from '../api'
import { useToastStore } from '../toast'
import ProductCard from '../components/ProductCard.vue'

const router = useRouter()
const toasts = useToastStore()

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)

const q = ref('')
const qInput = ref('')
const category = ref('')
const sort = ref('new')

const CATEGORIES = Object.entries(CATEGORY_NAMES)

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: page.value, page_size: pageSize, sort: sort.value })
    if (q.value) params.set('q', q.value)
    if (category.value) params.set('category', category.value)
    const data = await api(`/products?${params}`)
    items.value = data.items
    total.value = data.total
  } catch (e) {
    toasts.err('加载失败', e.message)
  } finally {
    loading.value = false
  }
}

function search() {
  q.value = qInput.value.trim()
  page.value = 1
  load()
}

function pickCategory(c) {
  category.value = c
  page.value = 1
  load()
}

function go(p) {
  page.value = p
  load()
  window.scrollTo({ top: 0 })
}

watch(sort, () => {
  page.value = 1
  load()
})

onMounted(load)
</script>

<template>
  <section class="hero">
    <div class="container">
      <h1>🌊 潮汐市集 · 让闲置流动起来</h1>
      <p>C2C 校园闲置交易平台 —— 发布、审核、抢购、支付、实时通知，全流程体验</p>
    </div>
  </section>

  <div class="container">
    <div class="toolbar">
      <input
        v-model="qInput"
        class="input"
        placeholder="搜索闲置好物，如：键盘 / 相机 / CSAPP"
        @keyup.enter="search"
      />
      <button class="btn btn-primary" @click="search">搜索</button>
      <select v-model="sort" class="select">
        <option value="new">最新发布</option>
        <option value="price_asc">价格从低到高</option>
        <option value="price_desc">价格从高到低</option>
      </select>
    </div>

    <div class="chips">
      <button class="chip" :class="{ active: category === '' }" @click="pickCategory('')">全部</button>
      <button
        v-for="[key, name] in CATEGORIES"
        :key="key"
        class="chip"
        :class="{ active: category === key }"
        @click="pickCategory(key)"
      >{{ name }}</button>
    </div>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="items.length === 0" class="empty">没有找到相关商品，换个关键词试试？</div>
    <div v-else class="product-grid">
      <ProductCard
        v-for="p in items"
        :key="p.id"
        :product="p"
        @click="router.push(`/product/${p.id}`)"
      />
    </div>

    <div v-if="total > pageSize" class="pager">
      <button class="btn btn-sm" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
      <span class="muted">第 {{ page }} / {{ Math.ceil(total / pageSize) }} 页 · 共 {{ total }} 件</span>
      <button class="btn btn-sm" :disabled="page >= Math.ceil(total / pageSize)" @click="go(page + 1)">下一页</button>
    </div>
  </div>
</template>
