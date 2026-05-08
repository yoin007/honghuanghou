<template>
  <div class="app-container">
    <el-container>
      <el-header class="app-header" height="auto">
        <div class="header-inner">
          <slot name="header-top">
            <div class="header-top">
              <h1 class="app-title">数字天龙</h1>
              <div class="header-right-actions">
                <slot name="class-selector"></slot>
                <div class="auth-actions">
                  <template v-if="isLoggedIn">
                    <span class="user-greeting hidden-xs-only">你好, {{ username }}</span>
                    <el-button type="danger" size="small" @click="$emit('logout')">退出</el-button>
                  </template>
                  <el-button v-else type="primary" size="small" @click="$emit('login-click')">登录</el-button>
                </div>
              </div>
            </div>
          </slot>
          <slot name="navigation"></slot>
        </div>
      </el-header>

      <el-container class="main-container">
        <el-main class="app-main">
          <slot name="main"></slot>
        </el-main>
      </el-container>

      <el-footer class="app-footer" height="40px">
        <div class="footer-content">
          <span>© 2026 数字天龙 - 技术田言校园综合管理系统 | Developer：Tech_T | Wechat：Tech_T</span>
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
defineProps({
  isLoggedIn: {
    type: Boolean,
    default: false
  },
  username: {
    type: String,
    default: ''
  }
})

defineEmits(['logout', 'login-click'])
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #249ee0;
  color: #303133;
  padding: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 2;
  flex-shrink: 0;
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  flex-direction: column;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
}

.app-title {
  margin: 0;
  font-size: 1.5rem;
  color: #fff;
  white-space: nowrap;
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.auth-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-greeting {
  color: #fff;
  font-size: 0.9rem;
}

.main-container {
  flex: 1;
  min-height: 0;
  display: flex;
}

.app-main {
  flex: 1;
  padding: 5rem 1rem 1rem;
  overflow-y: auto;
  background-color: var(--background-color);
  position: relative;
}

.app-footer {
  background-color: #f5f5f5;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.footer-content {
  text-align: center;
  color: #909399;
  font-size: 12px;
  line-height: 40px;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .app-header {
    height: auto !important;
    padding: 0.5rem;
  }

  .header-top {
    flex-direction: column;
    height: auto;
    padding: 10px 0;
    align-items: stretch;
  }

  .app-title {
    text-align: center;
    margin-bottom: 10px;
    font-size: 1.2rem;
  }

  .header-right-actions {
    flex-direction: column;
    width: 100%;
    gap: 10px;
  }

  .auth-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .hidden-xs-only {
    display: none;
  }

  .app-main {
    padding: 10px;
  }
}

@media screen and (max-width: 576px) {
  .app-main {
    padding: 0.5rem;
  }
}
</style>