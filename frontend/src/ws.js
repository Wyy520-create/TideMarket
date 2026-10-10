// WebSocket 连接管理：登录后建立连接，断线指数退避自动重连。
import { useUserStore } from './store'
import { useToastStore } from './toast'

let ws = null
let retry = 0
let closedByUser = false

export function connectWs() {
  const store = useUserStore()
  if (!store.token) return
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  closedByUser = false

  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws?token=${store.token}`)

  ws.onopen = () => {
    retry = 0
  }
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      useToastStore().push(msg.title, msg.body, 'info')
      const store2 = useUserStore()
      store2.unread += 1
    } catch {
      /* 忽略无法解析的消息 */
    }
  }
  ws.onclose = () => {
    ws = null
    if (!closedByUser && useUserStore().token && retry < 8) {
      retry += 1
      const delay = Math.min(15000, 500 * 2 ** retry)
      setTimeout(connectWs, delay)
    }
  }
  ws.onerror = () => ws?.close()
}

export function disconnectWs() {
  closedByUser = true
  retry = 99
  ws?.close()
  ws = null
}
