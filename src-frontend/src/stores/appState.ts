import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import type { ConnectionStatus } from '@/services/signalController'
import { signalController } from '@/services/signalController'
import { RECORDING_DEFAULT_LANGUAGE } from '@/constants'

// 通知其他窗口设置已变更
function notifySettingsChanged() {
  invoke('broadcast_settings_changed', { settings: {} }).catch(() => {})
}

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
  // 快捷键配置
  openSettingsShortcut: 'app-open-settings-shortcut',
}

// 快捷键配置类型
export interface ShortcutConfig {
  modifiers: string[]
  key: string
}

// 默认打开设置快捷键（macOS: Cmd+,  Windows/Linux: Ctrl+,）
const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
const DEFAULT_OPEN_SETTINGS_SHORTCUT: ShortcutConfig = {
  modifiers: [isMac ? 'Meta' : 'Ctrl'],
  key: ','
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

  // 快捷键配置
  const savedOpenSettingsShortcut = localStorage.getItem(STORAGE_KEYS.openSettingsShortcut)

  return {
    asrLanguage: savedAsrLang || RECORDING_DEFAULT_LANGUAGE,
    targetLanguage: savedTargetLang || '',
    correctionEnabled: savedCorrection !== null ? savedCorrection === 'true' : true,
    // LLM 配置
    llmApiKey: savedLlmApiKey || 'ollama',
    llmApiBase: savedLlmApiBase || 'http://localhost:11434/v1',
    llmModel: savedLlmModel || 'gpt-4o-mini',
    llmTimeout: savedLlmTimeout ? parseInt(savedLlmTimeout) : 10,
    llmTemperature: savedLlmTemperature ? parseFloat(savedLlmTemperature) : 0.3,
    // ASR 配置
    asrModelPath: savedAsrModelPath || '',
    // 快捷键配置
    openSettingsShortcut: savedOpenSettingsShortcut
      ? JSON.parse(savedOpenSettingsShortcut)
      : DEFAULT_OPEN_SETTINGS_SHORTCUT,
  }
}

// 消息记录类型
export interface MessageRecord {
  id: number
  text: string
  original?: string
  timestamp: number
  duration?: number  // 音频时长（秒）
}

export const useAppState = defineStore('appState', () => {
  const status = ref<AppStatus>('idle')
  const connectionStatus = ref<ConnectionStatus>('disconnected')
  const retryCount = ref(0)
  const currentTranscript = ref('')
  const originalTranscript = ref('')
  const errorMessage = ref('')

  // 消息历史（最多保留 10 条）
  const messageHistory = ref<MessageRecord[]>([])
  let messageIdCounter = 0

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

  // 快捷键配置
  const openSettingsShortcut = ref<ShortcutConfig>(savedSettings.openSettingsShortcut)

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

  // 添加最终结果到历史记录（只在收到 transcription 消息时调用）
  function addToHistory(text: string, original?: string, duration?: number) {
    if (text) {
      messageHistory.value.unshift({
        id: ++messageIdCounter,
        text,
        original,
        timestamp: Date.now(),
        duration
      })
      // 保留最近 10 条
      if (messageHistory.value.length > 10) {
        messageHistory.value.pop()
      }
    }
  }

  // 更新最近一条历史记录的文本（校正完成时调用，保留 original）
  function updateLatestHistory(text: string) {
    const current = messageHistory.value[0]
    if (text && current) {
      // 使用 splice 触发 Vue 响应式更新，只更新 text
      messageHistory.value.splice(0, 1, {
        id: current.id,
        text,
        original: current.original,
        timestamp: Date.now(),
        duration: current.duration
      })
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
    notifySettingsChanged()
  }

  function setTargetLanguage(lang: string) {
    targetLanguage.value = lang
    localStorage.setItem(STORAGE_KEYS.targetLanguage, lang)
    syncConfigToBackend()
    notifySettingsChanged()
  }

  function setCorrectionEnabled(enabled: boolean) {
    correctionEnabled.value = enabled
    localStorage.setItem(STORAGE_KEYS.correctionEnabled, String(enabled))
    syncConfigToBackend()
    notifySettingsChanged()
  }

  // LLM 配置 setters
  function setLlmApiKey(apiKey: string) {
    llmApiKey.value = apiKey
    localStorage.setItem(STORAGE_KEYS.llmApiKey, apiKey)
    syncLlmConfigToBackend()
    notifySettingsChanged()
  }

  function setLlmApiBase(apiBase: string) {
    llmApiBase.value = apiBase
    localStorage.setItem(STORAGE_KEYS.llmApiBase, apiBase)
    syncLlmConfigToBackend()
    notifySettingsChanged()
  }

  function setLlmModel(model: string) {
    llmModel.value = model
    localStorage.setItem(STORAGE_KEYS.llmModel, model)
    syncLlmConfigToBackend()
    notifySettingsChanged()
  }

  function setLlmTimeout(timeout: number) {
    llmTimeout.value = timeout
    localStorage.setItem(STORAGE_KEYS.llmTimeout, String(timeout))
    syncLlmConfigToBackend()
    notifySettingsChanged()
  }

  function setLlmTemperature(temperature: number) {
    llmTemperature.value = temperature
    localStorage.setItem(STORAGE_KEYS.llmTemperature, String(temperature))
    syncLlmConfigToBackend()
    notifySettingsChanged()
  }

  // ASR 配置 setter
  function setAsrModelPath(path: string) {
    asrModelPath.value = path
    localStorage.setItem(STORAGE_KEYS.asrModelPath, path)
    syncConfigToBackend()
    notifySettingsChanged()
  }

  // 快捷键配置 setter
  function setOpenSettingsShortcut(shortcut: ShortcutConfig) {
    openSettingsShortcut.value = shortcut
    localStorage.setItem(STORAGE_KEYS.openSettingsShortcut, JSON.stringify(shortcut))
    notifySettingsChanged()
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
        asrModelPath: asrModelPath.value || undefined,
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

  // 从 localStorage 重新加载配置（用于跨窗口同步）
  function reloadFromStorage() {
    const settings = loadSettings()
    applySettings(settings)
  }

  // 从事件数据应用设置（用于跨窗口同步）
  function applySettings(settings: Record<string, any>) {
    if (settings.asrLanguage !== undefined) asrLanguage.value = settings.asrLanguage
    if (settings.targetLanguage !== undefined) targetLanguage.value = settings.targetLanguage
    if (settings.correctionEnabled !== undefined) correctionEnabled.value = settings.correctionEnabled
    if (settings.llmApiKey !== undefined) llmApiKey.value = settings.llmApiKey
    if (settings.llmApiBase !== undefined) llmApiBase.value = settings.llmApiBase
    if (settings.llmModel !== undefined) llmModel.value = settings.llmModel
    if (settings.llmTimeout !== undefined) llmTimeout.value = settings.llmTimeout
    if (settings.llmTemperature !== undefined) llmTemperature.value = settings.llmTemperature
    if (settings.asrModelPath !== undefined) asrModelPath.value = settings.asrModelPath
    if (settings.openSettingsShortcut !== undefined) openSettingsShortcut.value = settings.openSettingsShortcut
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
    // 消息历史
    messageHistory,
    // LLM 配置
    llmApiKey,
    llmApiBase,
    llmModel,
    llmTimeout,
    llmTemperature,
    // ASR 配置
    asrModelPath,
    // 快捷键配置
    openSettingsShortcut,
    // 方法
    setStatus,
    setConnectionStatus,
    setTranscript,
    addToHistory,
    updateLatestHistory,
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
    // 快捷键配置方法
    setOpenSettingsShortcut,
    syncLlmConfigToBackend,
    reset,
    reloadFromStorage,
    applySettings,
  }
})
