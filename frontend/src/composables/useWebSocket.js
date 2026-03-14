// WebSocket Composable
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

export function useWebSocket(url = 'ws://localhost:14600/ws') {
  const ws = ref(null)
  const isConnected = ref(false)
  const messages = ref([])
  const reconnectInterval = 3000
  let reconnectTimer = null

  const connect = (userId = 'anonymous', room = null) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return
    }

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      isConnected.value = true
      // 发送身份消息
      ws.value.send(JSON.stringify({ user_id: userId, room }))
      console.log('WebSocket connected')
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        messages.value.push(data)
        handleMessage(data)
      } catch (e) {
        console.error('WebSocket message parse error:', e)
      }
    }

    ws.value.onclose = () => {
      isConnected.value = false
      console.log('WebSocket disconnected')
      // 自动重连
      reconnectTimer = setTimeout(() => {
        connect(userId, room)
      }, reconnectInterval)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  const handleMessage = (data) => {
    switch (data.type) {
      case 'homework_update':
        ElMessage.info(`作业更新: ${data.data.action}`)
        break
      case 'schedule_update':
        ElMessage.info('课表已更新')
        break
      case 'system':
        console.log('System:', data.content)
        break
      case 'pong':
        // 心跳响应
        break
    }
  }

  const send = (message) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    }
  }

  const ping = () => {
    send({ type: 'ping' })
  }

  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    isConnected.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    messages,
    connect,
    disconnect,
    send,
    ping
  }
}
