<script setup>
import { useToastStore } from '../toast'

const store = useToastStore()
</script>

<template>
  <div class="toast-wrap">
    <div v-for="t in store.items" :key="t.id" class="toast" :class="t.type" @click="store.remove(t.id)">
      <div class="toast-title">{{ t.title }}</div>
      <div v-if="t.body" class="toast-body">{{ t.body }}</div>
    </div>
  </div>
</template>
