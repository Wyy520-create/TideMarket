<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, CATEGORY_NAMES } from '../api'
import { useToastStore } from '../toast'

const router = useRouter()
const toasts = useToastStore()

const title = ref('')
const description = ref('')
const priceYuan = ref('')
const category = ref('digital')
const stock = ref(1)
const images = ref([])
const uploading = ref(false)
const pending = ref(false)
const error = ref('')

const CATEGORIES = Object.entries(CATEGORY_NAMES)

async function onPickFiles(e) {
  const files = [...e.target.files].slice(0, 4 - images.value.length)
  e.target.value = ''
  for (const f of files) {
    uploading.value = true
    try {
      const fd = new FormData()
      fd.append('file', f)
      const data = await api('/upload', { method: 'POST', body: fd })
      images.value.push(data.url)
    } catch (err) {
      toasts.err('图片上传失败', err.message)
    } finally {
      uploading.value = false
    }
  }
}

async function submit() {
  error.value = ''
  const price = Math.round(parseFloat(priceYuan.value) * 100)
  if (!price || price <= 0) {
    error.value = '请输入有效的价格'
    return
  }
  pending.value = true
  try {
    await api('/products', {
      method: 'POST',
      body: {
        title: title.value.trim(),
        description: description.value.trim(),
        price,
        category: category.value,
        stock: Number(stock.value),
        images: images.value,
      },
    })
    toasts.ok('发布成功', '商品已提交，等待管理员审核通过后自动上架')
    router.push('/')
  } catch (e) {
    error.value = e.message
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="card form-card">
    <h2>发布闲置</h2>
    <p class="muted" style="font-size: 13px; margin-top: -6px">商品提交后需管理员审核，通过后对全部买家可见。</p>

    <form @submit.prevent="submit">
      <div class="form-row">
        <label>商品标题</label>
        <input v-model="title" class="input" placeholder="如：九成新机械键盘" required minlength="2" maxlength="64" />
      </div>
      <div class="form-row">
        <label>描述</label>
        <textarea v-model="description" class="textarea" placeholder="成色、入手渠道、瑕疵、交易方式…" maxlength="2000" />
      </div>
      <div class="form-grid-2">
        <div class="form-row">
          <label>价格（元）</label>
          <input v-model="priceYuan" type="number" step="0.01" min="0.01" class="input" placeholder="0.00" required />
        </div>
        <div class="form-row">
          <label>库存（件）</label>
          <input v-model="stock" type="number" min="1" max="999" class="input" required />
        </div>
      </div>
      <div class="form-row">
        <label>分类</label>
        <select v-model="category" class="select">
          <option v-for="[key, name] in CATEGORIES" :key="key" :value="key">{{ name }}</option>
        </select>
      </div>
      <div class="form-row">
        <label>图片（最多 4 张，单张 ≤ 2MB）</label>
        <div class="thumbs">
          <div v-for="(url, i) in images" :key="url" class="thumb">
            <img :src="url" alt="商品图" />
            <button type="button" class="del" @click="images.splice(i, 1)">×</button>
          </div>
          <label v-if="images.length < 4" class="upload-box" :style="{ opacity: uploading ? .5 : 1 }">
            {{ uploading ? '…' : '+' }}
            <input type="file" accept="image/*" multiple hidden @change="onPickFiles" />
          </label>
        </div>
      </div>
      <div v-if="error" class="form-row error-text">{{ error }}</div>
      <div class="form-actions">
        <button class="btn btn-primary" :disabled="pending || uploading">{{ pending ? '提交中…' : '提交审核' }}</button>
      </div>
    </form>
  </div>
</template>
