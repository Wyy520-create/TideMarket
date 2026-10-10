import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from './store'

const routes = [
  { path: '/', component: () => import('./views/HomeView.vue') },
  { path: '/product/:id', component: () => import('./views/ProductDetailView.vue') },
  { path: '/login', component: () => import('./views/LoginView.vue') },
  { path: '/publish', component: () => import('./views/PublishView.vue'), meta: { requiresAuth: true } },
  { path: '/orders', component: () => import('./views/OrdersView.vue'), meta: { requiresAuth: true } },
  { path: '/notifications', component: () => import('./views/NotificationsView.vue'), meta: { requiresAuth: true } },
  { path: '/admin', component: () => import('./views/AdminView.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const store = useUserStore()
  if (to.meta.requiresAuth && !store.isLogin) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !store.isAdmin) {
    return { path: '/' }
  }
  return true
})

export default router
