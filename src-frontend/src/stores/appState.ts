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
  // LLM 配置
  llmApiKey: 'app-llm-api-key',
  llmApiBase: 'app-llm-api-base',
  llmModel: 'app-llm-model',
  llmTimeout: 'app-llm-timeout',
  llmTemperature: 'app-llm-temperature',
  // ASR 配置
  asrModelPath: 'app-asr-model-path',
}

// 从 localStorage 读取设置
function loadSettings() {
  const savedAsrLang = localStorage.getItem(STORAGE_KEYS.asrLanguage)
  const savedTargetLang = localStorage.getItem(STORAGE_KEYS.targetLanguage)
  const savedCorrection = localStorage.getItem(STORAGE_KEYS.correctionEnabled)

  // LLM 配置
  const savedLlmApiKey = localStorage.getItem(STORAGE_KEYS.llmApiKey)
  const savedLlmApiBase = localStorage.getItem(STORAGE_KEYS.llmApiBase)
  const savedLlmModel = localStorage.getItem(STORAGE_KEYS.llmModel)
  const savedLlmTimeout = localStorage.getItem(STORAGE_KEYS.llmTimeout)
  const savedLlmTemperature = localStorage.getItem(STORAGE_KEYS.llmTemperature)

  // ASR 配置
  const savedAsrModelPath = localStorage.getItem(STORAGE_KEYS.asrModelPath)

  return {
    asrLanguage: savedAsrLang || RECORDING_DEFAULT_LANGUAGE,
    targetLanguage: savedTargetLang || '',
    correctionEnabled: savedCorrection !== null ? savedCorrection === 'true' : true,
    // LLM 配置
    llmApiKey: savedLlmApiKey || '',
    llmApiBase: savedLlmApiBase || 'http://localhost:11434/v1',
    llmModel: savedLlmModel || 'gpt-4o-mini',
    llmTimeout: savedLlmTimeout ? parseInt(savedLlmTimeout) : 10,
    llmTemperature: savedLlmTemperature ? parseFloat(savedLlmTemperature) : 0.3,
    // ASR 配置
    asrModelPath: savedAsrModelPath || '',
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

  // LLM 配置
  const llmApiKey = ref(savedSettings.llmApiKey)
  const llmApiBase = ref(savedSettings.llmApiBase)
  const llmModel = ref(savedSettings.llmModel)
  const llmTimeout = ref(savedSettings.llmTimeout)
  const llmTemperature = ref(savedSettings.llmTemperature)

  // ASR 配置
  const asrModelPath = ref(savedSettings.asrModelPath)

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

  // LLM 配置 setters
  function setLlmApiKey(apiKey: string) {
    llmApiKey.value = apiKey
    localStorage.setItem(STORAGE_KEYS.llmApiKey, apiKey)
    syncLlmConfigToBackend()
  }

  function setLlmApiBase(apiBase: string) {
    llmApiBase.value = apiBase
    localStorage.setItem(STORAGE_KEYS.llmApiBase, apiBase)
    syncLlmConfigToBackend()
  }

  function setLlmModel(model: string) {
    llmModel.value = model
    localStorage.setItem(STORAGE_KEYS.llmModel, model)
    syncLlmConfigToBackend()
  }

  function setLlmTimeout(timeout: number) {
    llmTimeout.value = timeout
    localStorage.setItem(STORAGE_KEYS.llmTimeout, String(timeout))
    syncLlmConfigToBackend()
  }

  function setLlmTemperature(temperature: number) {
    llmTemperature.value = temperature
    localStorage.setItem(STORAGE_KEYS.llmTemperature, String(temperature))
    syncLlmConfigToBackend()
  }

  // ASR 配置 setter
  function setAsrModelPath(path: string) {
    asrModelPath.value = path
    localStorage.setItem(STORAGE_KEYS.asrModelPath, path)
  }

  // 同步 LLM 配置到后端
  function syncLlmConfigToBackend() {
    if (isConnected.value) {
      signalController.updateLlmConfig({
        api_key: llmApiKey.value || undefined,
        api_base: llmApiBase.value || undefined,
        model: llmModel.value,
        timeout: llmTimeout.value,
        temperature: llmTemperature.value,
      })
    }
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
    // LLM 配置
    llmApiKey,
    llmApiBase,
    llmModel,
    llmTimeout,
    llmTemperature,
    // ASR 配置
    asrModelPath,
    // 方法
    setStatus,
    setConnectionStatus,
    setTranscript,
    setError,
    setWaveformLevels,
    resetWaveformLevels,
    setAsrLanguage,
    setTargetLanguage,
    setCorrectionEnabled,
    // LLM 配置方法
    setLlmApiKey,
    setLlmApiBase,
    setLlmModel,
    setLlmTimeout,
    setLlmTemperature,
    // ASR 配置方法
    setAsrModelPath,
    syncLlmConfigToBackend,
    reset,
  }
})
