import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../utils/api'

export const useAppStore = defineStore('app', () => {
  const classCode = ref(localStorage.getItem('selectedClassCode') || '')
  const classCodes = ref([])
  const loading = ref(false)

  const getClassCode = () => {
    const code = document.cookie.split('; ').find(row => row.startsWith('classCode='))
    return code ? code.split('=')[1] : null
  }

  const fetchClassCodes = async () => {
    loading.value = true
    try {
      let clientIp = ''
      if (import.meta.env.DEV) {
        try {
          const ipRes = await fetch('/__client-ip')
          if (ipRes.ok) {
            const data = await ipRes.json()
            clientIp = data.ip
          }
        } catch (e) {
          console.warn('无法获取开发环境 IP', e)
        }
      }

      const response = await api.get('/api/class-codes/', {
        params: { ip: clientIp }
      })
      if (response.data && Array.isArray(response.data.class_codes)) {
        classCodes.value = response.data.class_codes
        const savedCode = localStorage.getItem('selectedClassCode')
        if (savedCode && classCodes.value.includes(savedCode)) {
          classCode.value = savedCode
        }
        if (classCodes.value.length === 1 && !classCode.value) {
          classCode.value = classCodes.value[0]
          handleClassChange(classCodes.value[0])
        }
      }
    } catch (error) {
      console.error('Error fetching class codes:', error)
    } finally {
      loading.value = false
    }
  }

  const handleClassChange = (value) => {
    const cookieClassCode = getClassCode()
    classCode.value = value
    localStorage.setItem('selectedClassCode', value)
    document.cookie = `classCode=${value}; path=/`
    if (String(cookieClassCode) !== String(value)) {
      window.location.reload()
    }
  }

  const initClassCode = () => {
    const savedClassCode = getClassCode()
    if (savedClassCode) {
      classCode.value = savedClassCode
    }
  }

  return {
    classCode,
    classCodes,
    loading,
    fetchClassCodes,
    handleClassChange,
    initClassCode,
    getClassCode
  }
})
