import { defineStore } from 'pinia'
import { api } from './api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('tm_token') || '',
    user: JSON.parse(localStorage.getItem('tm_user') || 'null'),
    unread: 0,
  }),
  getters: {
    isLogin: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    setAuth(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('tm_token', token)
      localStorage.setItem('tm_user', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.user = null
      this.unread = 0
      localStorage.removeItem('tm_token')
      localStorage.removeItem('tm_user')
    },
    async login(username, password) {
      const data = await api('/auth/login', {
        method: 'POST',
        body: { username, password },
      })
      this.setAuth(data.token, data.user)
    },
    async register(username, email, password) {
      const data = await api('/auth/register', {
        method: 'POST',
        body: { username, email, password },
      })
      this.setAuth(data.token, data.user)
    },
    async refreshUnread() {
      if (!this.isLogin) return
      const list = await api('/notifications')
      this.unread = list.filter((n) => !n.is_read).length
    },
  },
})
