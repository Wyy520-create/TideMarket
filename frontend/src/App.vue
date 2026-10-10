<script setup>
import { onMounted, watch } from 'vue'
import { useUserStore } from './store'
import { connectWs, disconnectWs } from './ws'
import NavBar from './components/NavBar.vue'
import ToastHost from './components/Toast.vue'

const store = useUserStore()

watch(
  () => store.token,
  (token) => {
    if (token) {
      connectWs()
      store.refreshUnread()
    } else {
      disconnectWs()
    }
  },
  { immediate: true },
)

onMounted(() => {
  if (store.isLogin) store.refreshUnread()
})
</script>

<template>
  <NavBar />
  <main class="container">
    <router-view />
  </main>
  <ToastHost />
</template>
