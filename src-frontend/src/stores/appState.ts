import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type AppStatus = 'idle' | 'listening' | 'processing' | 'speaking' | 'error'

export const useAppState = defineStore('appState', () => {
  const status = ref<AppStatus>('idle')
  const isConnected = ref(false)
  const currentTranscript = ref('')
  const errorMessage = ref('')

  const isActive = computed(() =>
    status.value === 'listening' || status.value === 'processing'
  )

  function setStatus(newStatus: AppStatus) {
    status.value = newStatus
  }

  function setConnected(connected: boolean) {
    isConnected.value = connected
  }

  function setTranscript(text: string) {
    currentTranscript.value = text
  }

  function setError(message: string) {
    errorMessage.value = message
    status.value = 'error'
  }

  function reset() {
    status.value = 'idle'
    currentTranscript.value = ''
    errorMessage.value = ''
  }

  return {
    status,
    isConnected,
    currentTranscript,
    errorMessage,
    isActive,
    setStatus,
    setConnected,
    setTranscript,
    setError,
    reset,
  }
})
