import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type AppStatus = 'idle' | 'listening' | 'transcribing' | 'correcting' | 'speaking' | 'error'

export const useAppState = defineStore('appState', () => {
  const status = ref<AppStatus>('idle')
  const isConnected = ref(false)
  const currentTranscript = ref('')
  const originalTranscript = ref('')
  const errorMessage = ref('')

  const isActive = computed(() =>
    status.value === 'listening' || status.value === 'transcribing' || status.value === 'correcting'
  )

  function setStatus(newStatus: AppStatus) {
    status.value = newStatus
  }

  function setConnected(connected: boolean) {
    isConnected.value = connected
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
    isConnected,
    currentTranscript,
    originalTranscript,
    errorMessage,
    isActive,
    setStatus,
    setConnected,
    setTranscript,
    setError,
    reset,
  }
})
