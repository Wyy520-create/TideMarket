// 统一 API 客户端：注入 token、解析错误、处理表单上传。

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function detailToMessage(detail) {
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg).join('；')
  }
  return detail || '请求失败，请稍后再试'
}

export async function api(path, { method = 'GET', body, headers = {} } = {}) {
  const token = localStorage.getItem('tm_token')
  const isForm = body instanceof FormData
  const res = await fetch('/api' + path, {
    method,
    headers: {
      ...(body && !isForm ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = null
  }
  if (!res.ok) {
    throw new ApiError(res.status, detailToMessage(data?.detail))
  }
  return data
}

export const fen2yuan = (fen) => (fen / 100).toFixed(2)

export const CATEGORY_NAMES = {
  digital: '数码',
  book: '图书',
  clothes: '服饰',
  life: '生活',
  other: '其他',
}

export const ORDER_STATUS = {
  pending: { text: '待支付', cls: 'warn' },
  paid: { text: '已支付', cls: 'ok' },
  cancelled: { text: '已取消', cls: 'muted' },
}
