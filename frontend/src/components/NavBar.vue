<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store'

const store = useUserStore()
const route = useRoute()
const router = useRouter()

function logout() {
  store.logout()
  router.push('/')
}
</script>

<template>
  <header class="navbar">
    <div class="navbar-inner">
      <router-link to="/" class="logo">🌊 潮汐市集</router-link>
      <nav class="nav-links">
        <router-link to="/" :class="{ active: route.path === '/' }">首页</router-link>
        <router-link v-if="store.isLogin" to="/publish" :class="{ active: route.path === '/publish' }">发布闲置</router-link>
        <router-link v-if="store.isLogin" to="/orders" :class="{ active: route.path === '/orders' }">我的订单</router-link>
        <router-link v-if="store.isAdmin" to="/admin" :class="{ active: route.path === '/admin' }">管理后台</router-link>
      </nav>
      <div class="nav-right">
        <router-link v-if="store.isLogin" to="/notifications" class="bell" title="通知中心">
          🔔
          <span v-if="store.unread > 0" class="bell-badge">{{ store.unread > 99 ? '99+' : store.unread }}</span>
        </router-link>
        <div v-if="store.isLogin" class="user-chip">
          <span class="avatar">👤</span>
          <span>{{ store.user?.username }}</span>
          <span v-if="store.isAdmin" class="role-tag">管理员</span>
          <button class="link-btn" @click="logout">退出</button>
        </div>
        <router-link v-else to="/login" class="link-btn">登录 / 注册</router-link>
      </div>
    </div>
  </header>
</template>
