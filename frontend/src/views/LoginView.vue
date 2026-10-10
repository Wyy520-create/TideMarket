<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store'
import { useToastStore } from '../toast'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const toasts = useToastStore()

const mode = ref('login')
const username = ref('')
const email = ref('')
const password = ref('')
const pending = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  pending.value = true
  try {
    if (mode.value === 'login') {
      await store.login(username.value.trim(), password.value)
      toasts.ok('登录成功', `欢迎回来，${store.user?.username}`)
    } else {
      await store.register(username.value.trim(), email.value.trim(), password.value)
      toasts.ok('注册成功', '已自动登录')
    }
    router.push(route.query.redirect || '/')
  } catch (e) {
    error.value = e.message
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="card form-card">
    <h2>{{ mode === 'login' ? '登录潮汐市集' : '注册新账号' }}</h2>
    <p class="muted" style="font-size: 13px; margin-top: -6px">
      演示账号：买家 ahai / 卖家 xiaoyu / 管理员 admin，密码均为 <code>xxx123456</code> 格式（见 README）
    </p>

    <form @submit.prevent="submit">
      <div class="form-row">
        <label>用户名</label>
        <input v-model="username" class="input" placeholder="2-32 位字符" required />
      </div>
      <div v-if="mode === 'register'" class="form-row">
        <label>邮箱</label>
        <input v-model="email" type="email" class="input" placeholder="you@example.com" required />
      </div>
      <div class="form-row">
        <label>密码</label>
        <input v-model="password" type="password" class="input" placeholder="至少 6 位" required minlength="6" />
      </div>
      <div v-if="error" class="form-row error-text">{{ error }}</div>
      <div class="form-actions">
        <button class="btn btn-primary" :disabled="pending">{{ pending ? '提交中…' : mode === 'login' ? '登录' : '注册并登录' }}</button>
      </div>
    </form>

    <div style="margin-top: 16px; font-size: 13px; text-align: center">
      <a href="javascript:;" class="muted" @click="mode = mode === 'login' ? 'register' : 'login'; error = ''">
        {{ mode === 'login' ? '没有账号？点击注册' : '已有账号？点击登录' }}
      </a>
    </div>
  </div>
</template>
