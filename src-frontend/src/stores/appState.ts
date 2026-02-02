import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionStatus } from '@/services/signalController'
import { signalController } from '@/services/signalController'
import { RECORDING_DEFAULT_LANGUAGE } from '@/constants'

export type AppStatus = 'idle' | 'starting' | 'listening' | 'transcribing' | 'correcting' | 'translating' | 'speaking' | 'error'

// localStorage keys
const STORAGE_KEYS = {
  asrLanguage: 'app-asr-language',
  targetLanguage: 'app-target-language',
  correctionEnabled: 'app-correction-enabled',
}

// 从 localStorage 读取设置
function loadSettings() {
  const savedAsrLang = localStorage.getItem(STORAGE_KEYS.asrLanguage)
  const savedTargetLang = localStorage.getItem(STORAGE_KEYS.targetLanguage)
  const savedCorrection = localStorage.getItem(STORAGE_KEYS.correctionEnabled)

  return {
    asrLanguage: savedAsrLang || RECORDING_DEFAULT_LANGUAGE,
    targetLanguage: savedTargetLang || '',
    correctionEnabled: savedCorrection !== null ? savedCorrection === 'true' : true,
  }
}

export const useAppState = defineStore('appState', () => {
  const status = ref<AppStatus>('idle')
  const connectionStatus = ref<ConnectionStatus>('disconnected')
  const retryCount = ref(0)
  const currentTranscript = ref('')
  const originalTranscript = ref('')
  const errorMessage = ref('')

  // 波形数据 (5 个归一化值 0-1)
  const waveformLevels = ref<number[]>([0, 0, 0, 0, 0])

  // 录音配置（从 localStorage 加载）
  const savedSettings = loadSettings()
  const asrLanguage = ref(savedSettings.asrLanguage)
  const targetLanguage = ref(savedSettings.targetLanguage)
  const correctionEnabled = ref(savedSettings.correctionEnabled)

  const isConnected = computed(() => connectionStatus.value === 'connected')

  const isActive = computed(() =>
    status.value !== 'idle' && status.value !== 'error'
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

  function setWaveformLevels(levels: number[]) {
    waveformLevels.value = levels
  }

  function resetWaveformLevels() {
    waveformLevels.value = [0, 0, 0, 0, 0]
  }

  function setAsrLanguage(lang: string) {
    asrLanguage.value = lang
    localStorage.setItem(STORAGE_KEYS.asrLanguage, lang)
    syncConfigToBackend()
  }

  function setTargetLanguage(lang: string) {
    targetLanguage.value = lang
    localStorage.setItem(STORAGE_KEYS.targetLanguage, lang)
    syncConfigToBackend()
  }

  function setCorrectionEnabled(enabled: boolean) {
    correctionEnabled.value = enabled
    localStorage.setItem(STORAGE_KEYS.correctionEnabled, String(enabled))
    syncConfigToBackend()
  }

  // 同步配置到后端（已连接时发送）
  function syncConfigToBackend() {
    if (isConnected.value) {
      signalController.updateConfig({
        language: asrLanguage.value,
        correctionEnabled: correctionEnabled.value,
        targetLanguage: targetLanguage.value || undefined,
      })
    }
  }

  function reset() {
    status.value = 'idle'
    currentTranscript.value = ''
    originalTranscript.value = ''
    errorMessage.value = ''
    waveformLevels.value = [0, 0, 0, 0, 0]
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
    asrLanguage,
    targetLanguage,
    correctionEnabled,
    waveformLevels,
    setStatus,
    setConnectionStatus,
    setTranscript,
    setError,
    setWaveformLevels,
    resetWaveformLevels,
    setAsrLanguage,
    setTargetLanguage,
    setCorrectionEnabled,
    reset,
  }
})
