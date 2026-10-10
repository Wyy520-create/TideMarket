import { defineStore } from 'pinia'

let seq = 0

export const useToastStore = defineStore('toast', {
  state: () => ({ items: [] }),
  actions: {
    push(title, body = '', type = 'info') {
      const id = ++seq
      this.items.push({ id, title, body, type })
      setTimeout(() => this.remove(id), 5000)
    },
    ok(title, body = '') {
      this.push(title, body, 'ok')
    },
    err(title, body = '') {
      this.push(title, body, 'err')
    },
    remove(id) {
      this.items = this.items.filter((t) => t.id !== id)
    },
  },
})
