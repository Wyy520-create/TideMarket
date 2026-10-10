<script setup>
import { CATEGORY_NAMES, fen2yuan } from '../api'

defineProps({
  product: { type: Object, required: true },
})

function onImgError(e) {
  e.target.style.display = 'none'
  e.target.nextElementSibling.style.display = 'flex'
}
</script>

<template>
  <div class="p-card">
    <div style="position: relative">
      <img
        v-if="product.images && product.images.length"
        class="p-cover"
        :src="product.images[0]"
        :alt="product.title"
        @error="onImgError"
      />
      <div
        class="p-cover"
        style="display: none; align-items: center; justify-content: center; font-size: 56px; background: linear-gradient(135deg, #a5f3fc, #e0f2fe)"
      >🌊</div>
      <span v-if="product.stock <= 0" class="badge muted" style="position: absolute; top: 8px; left: 8px">已售罄</span>
      <span v-else-if="product.stock === 1" class="badge warn" style="position: absolute; top: 8px; left: 8px">仅剩 1 件</span>
    </div>
    <div class="p-body">
      <div class="p-title">{{ product.title }}</div>
      <div class="p-meta">
        <span class="price">¥{{ fen2yuan(product.price) }}</span>
        <span class="p-seller">{{ CATEGORY_NAMES[product.category] || '其他' }} · {{ product.seller_name }}</span>
      </div>
    </div>
  </div>
</template>
