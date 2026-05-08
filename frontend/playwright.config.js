import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'https://localhost:3335',
    trace: 'on-first-retry',
    ignoreHTTPSErrors: true, // 忽略SSL错误（开发环境）
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'https://localhost:3335',
    reuseExistingServer: true, // 使用已启动的服务
    ignoreHTTPSErrors: true,
  },
})