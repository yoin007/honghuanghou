import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import { useResourcePermissionStore } from '@/stores/resourcePermission'

const app = createApp(App)
const pinia = createPinia()

// 全局配置axios
app.config.globalProperties.$axios = axios

app.use(pinia)
app.use(ElementPlus)

// 触发公开路由预拉（不阻塞挂载）——首次路由守卫会 await 这个 promise 后再判断。
// 失败不阻塞启动，isPublicPath 会 fallback 到路由 meta.requiresAuth。
useResourcePermissionStore(pinia).loadPublicRoutes().catch(() => {})

app.use(router)

app.mount('#app')
