import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'
import http from 'http'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_API_BASE_URL || 'http://localhost:14600'
  const useHttps = env.VITE_DEV_HTTPS === 'true'
  const devHost = env.VITE_DEV_HOST || 'localhost'
  const httpPort = Number(env.VITE_DEV_HTTP_PORT || 3333)
  const httpsPort = Number(env.VITE_DEV_HTTPS_PORT || 3334)
  const serverPort = useHttps ? httpsPort : httpPort
  const httpsConfig = useHttps ? true : undefined
  const origin = `${useHttps ? 'https' : 'http'}://${devHost}:${serverPort}`
  let extraHttpServer

  return {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src')
      }
    },
    optimizeDeps: {
      include: ['xlsx']
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'element-plus': ['element-plus'],
            'vue-vendor': ['vue', 'vue-router', 'pinia'],
            'utils': ['axios']
          }
        }
      }
    },
    server: {
      port: serverPort,
      host: '0.0.0.0',
      https: httpsConfig,
      origin,
      hmr: false,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
          timeout: 15000,
          proxyTimeout: 15000
        },
        '/static': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
          timeout: 15000,
          proxyTimeout: 15000
        }
      }
    },
    plugins: [
      useHttps ? basicSsl() : null,
      vue(),
      {
        name: 'log-with-time',
        configureServer(server) {
          if (useHttps && httpPort && httpPort !== serverPort) {
            extraHttpServer = http.createServer((req, res) => {
              server.middlewares(req, res, () => {
                res.statusCode = 404
                res.end()
              })
            })
            extraHttpServer.listen(httpPort, server.config.server.host)
            server.httpServer?.once('close', () => {
              extraHttpServer?.close()
            })
          }
          server.middlewares.use((req, res, next) => {
            const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || ''

            if (req.url === '/__client-ip') {
              res.statusCode = 200
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ip }))
              return
            }

            const east8 = new Date(Date.now() + 8 * 60 * 60 * 1000)
            const ts = east8.toISOString().replace('Z', '+08:00')
            console.log(`[${ts}] [${ip}] ${req.method} ${req.url}`)
            next()
          })
        }
      }
    ].filter(Boolean)
  }
})
