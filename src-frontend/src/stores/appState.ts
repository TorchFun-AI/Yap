import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionStatus } from '@/services/signalController'

export type AppStatus = 'idle' | 'listening' | 'transcribing' | 'correcting' | 'speaking' | 'error'

export const useAppState = defineStore('appState', () => {
  const status = ref<AppStatus>('idle')
  const connectionStatus = ref<ConnectionStatus>('disconnected')
  const retryCount = ref(0)
  const currentTranscript = ref('')
  const originalTranscript = ref('')
  const errorMessage = ref('')

  const isConnected = computed(() => connectionStatus.value === 'connected')

  const isActive = computed(() =>
    status.value === 'listening' || status.value === 'transcribing' || status.value === 'correcting'
  )

  function setStatus(newStatus: AppStatus) {
    status.value = newStatus
  }

  function setConnectionStatus(newStatus: ConnectionStatus, retry = 0) {
    connectionStatus.value = newStatus
    retryCount.value = retry
  }

  function setTranscript(text: string, original?: string) {
    currentTranscript.value = text
    if (original) {
      originalTranscript.value = original
    }
  }

  function setError(message: string) {
    errorMessage.value = message
    status.value = 'error'
  }

  function reset() {
    status.value = 'idle'
    currentTranscript.value = ''
    originalTranscript.value = ''
    errorMessage.value = ''
  }

  return {
    status,
    connectionStatus,
    retryCount,
    isConnected,
    currentTranscript,
    originalTranscript,
    errorMessage,
    isActive,
    setStatus,
    setConnectionStatus,
    setTranscript,
    setError,
    reset,
  }
})
