<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { invoke } from '@tauri-apps/api/core'
import { useAppState } from '@/stores/appState'
import { AppStatus } from '@/constants'
import { setLocale, getLocale } from '@/i18n'
import { logController } from '@/services/logController'
import { httpUrl } from '@/services/portService'
import { message } from 'ant-design-vue'

// 配置消息提示框
message.config({
  top: '60px',
  duration: 2,
})

const { t } = useI18n()

const props = defineProps<{
  isStandalone?: boolean
}>()

const emit = defineEmits<{
  close: []
  'start-drag': []
}>()

const appState = useAppState()

// 当前选中的设置标签
const activeTab = ref<'general' | 'voice' | 'llm' | 'asr' | 'debug'>('general')

// 录音中时禁用配置修改
const isRecording = computed(() =>
  appState.status === AppStatus.STARTING ||
  appState.status === AppStatus.LISTENING ||
  appState.status === AppStatus.TRANSCRIBING ||
  appState.status === AppStatus.CORRECTING ||
  appState.status === AppStatus.TRANSLATING ||
  appState.status === AppStatus.SPEAKING
)

// 动态生成 ASR 语言选项
const asrLanguageOptions = computed(() => [
  { value: 'auto', label: t('asrLanguages.auto') },
  { value: 'zh', label: t('asrLanguages.zh') },
  { value: 'en', label: t('asrLanguages.en') },
  { value: 'ja', label: t('asrLanguages.ja') },
  { value: 'ko', label: t('asrLanguages.ko') },
  { value: 'yue', label: t('asrLanguages.yue') },
])

// 动态生成输出方式选项
const autoInputModeOptions = computed(() => [
  { value: 'input', label: t('settings.autoInputMode.input') },
  { value: 'clipboard', label: t('settings.autoInputMode.clipboard') },
  { value: 'none', label: t('settings.autoInputMode.none') },
])

// 动态生成翻译语言选项
const translateLanguageOptions = computed(() => [
  { value: '', label: t('translateLanguages.none') },
  { value: '中文', label: t('translateLanguages.zh') },
  { value: 'English', label: t('translateLanguages.en') },
  { value: '日本語', label: t('translateLanguages.ja') },
  { value: '한국어', label: t('translateLanguages.ko') },
  { value: 'Français', label: t('translateLanguages.fr') },
  { value: 'Deutsch', label: t('translateLanguages.de') },
  { value: 'Español', label: t('translateLanguages.es') },
])

// 界面语言选项
const localeOptions = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
]

// 当前界面语言
const currentLocale = ref(getLocale())

// 快捷键设置
interface ShortcutConfig {
  modifiers: string[]
  key: string
}

const shortcutModifiers = ref<string[]>(['Alt'])
const shortcutKey = ref('F5')
const shortcutError = ref('')

// 打开设置快捷键
const openSettingsModifiers = ref<string[]>(appState.openSettingsShortcut.modifiers)
const openSettingsKey = ref(appState.openSettingsShortcut.key)
const openSettingsError = ref('')

// 修饰键选项
const modifierOptions = [
  { value: 'Alt', label: 'Alt/Option' },
  { value: 'Ctrl', label: 'Ctrl' },
  { value: 'Shift', label: 'Shift' },
  { value: 'Meta', label: 'Cmd/Win' },
]

// 按键选项
const keyOptions = [
  { value: ',', label: ',' },
  { value: 'F1', label: 'F1' },
  { value: 'F2', label: 'F2' },
  { value: 'F3', label: 'F3' },
  { value: 'F4', label: 'F4' },
  { value: 'F5', label: 'F5' },
  { value: 'F6', label: 'F6' },
  { value: 'F7', label: 'F7' },
  { value: 'F8', label: 'F8' },
  { value: 'F9', label: 'F9' },
  { value: 'F10', label: 'F10' },
  { value: 'F11', label: 'F11' },
  { value: 'F12', label: 'F12' },
  { value: 'A', label: 'A' },
  { value: 'B', label: 'B' },
  { value: 'C', label: 'C' },
  { value: 'D', label: 'D' },
  { value: 'E', label: 'E' },
  { value: 'F', label: 'F' },
  { value: 'G', label: 'G' },
  { value: 'H', label: 'H' },
  { value: 'I', label: 'I' },
  { value: 'J', label: 'J' },
  { value: 'K', label: 'K' },
  { value: 'L', label: 'L' },
  { value: 'M', label: 'M' },
  { value: 'N', label: 'N' },
  { value: 'O', label: 'O' },
  { value: 'P', label: 'P' },
  { value: 'Q', label: 'Q' },
  { value: 'R', label: 'R' },
  { value: 'S', label: 'S' },
  { value: 'T', label: 'T' },
  { value: 'U', label: 'U' },
  { value: 'V', label: 'V' },
  { value: 'W', label: 'W' },
  { value: 'X', label: 'X' },
  { value: 'Y', label: 'Y' },
  { value: 'Z', label: 'Z' },
]

// LLM 模型选项（从 API 动态获取）
const llmModelOptions = ref<{value: string}[]>([])
const isLoadingModels = ref(false)

// 从 API 获取模型列表
async function fetchLlmModels() {
  const apiBase = appState.llmApiBase || 'http://localhost:11434/v1'
  isLoadingModels.value = true

  try {
    const headers: Record<string, string> = {}
    if (appState.llmApiKey) {
      headers['Authorization'] = `Bearer ${appState.llmApiKey}`
    }

    const res = await fetch(`${apiBase}/models`, { headers })
    if (res.ok) {
      const data = await res.json()
      const models = data.data || []
      llmModelOptions.value = models
        .map((m: any) => ({ value: m.id }))
        .sort((a: any, b: any) => a.value.localeCompare(b.value))
    }
  } catch (e) {
    console.error('Failed to fetch LLM models:', e)
    llmModelOptions.value = []
  } finally {
    isLoadingModels.value = false
  }
}

// API 地址变更时重新获取模型列表
function onApiBaseChange(value: string) {
  appState.setLlmApiBase(value)
  fetchLlmModels()
}

const onLocaleChange = (value: 'zh' | 'en') => {
  currentLocale.value = value
  setLocale(value)
  invoke('broadcast_settings_changed').catch(() => {})
}

// 加载快捷键设置
async function loadShortcutSettings() {
  try {
    const settings = await invoke<{ toggle_recording?: ShortcutConfig }>('get_shortcut_settings')
    if (settings.toggle_recording) {
      shortcutModifiers.value = settings.toggle_recording.modifiers
      shortcutKey.value = settings.toggle_recording.key
    }
  } catch (e) {
    console.error('Failed to load shortcut settings:', e)
  }
}

// 保存快捷键设置
async function saveShortcut() {
  shortcutError.value = ''
  if (shortcutModifiers.value.length === 0) {
    shortcutError.value = t('settings.shortcut.invalid')
    return
  }
  try {
    await invoke('update_shortcut', {
      modifiers: shortcutModifiers.value,
      key: shortcutKey.value,
    })
  } catch (e) {
    shortcutError.value = t('settings.shortcut.invalid')
    console.error('Failed to save shortcut:', e)
  }
}

// 保存打开设置快捷键
function saveOpenSettingsShortcut() {
  openSettingsError.value = ''
  if (openSettingsModifiers.value.length === 0) {
    openSettingsError.value = t('settings.shortcut.invalid')
    return
  }
  appState.setOpenSettingsShortcut({
    modifiers: openSettingsModifiers.value,
    key: openSettingsKey.value,
  })
}

// ASR 模型管理
interface LocalModel {
  id: string
  name: string
  size: string
}

interface AvailableModel {
  id: string
  name: string
  size: string
  description: string
  downloaded: boolean
}

const localModels = ref<LocalModel[]>([])
const availableModels = ref<AvailableModel[]>([])
const downloadingModels = ref<Set<string>>(new Set())
const downloadProgress = ref<Record<string, {
  progress: number
  downloaded: string
  total: string
  speed: string
  eta?: string
  isFileCount?: boolean
}>>({})

// 模型校验和删除状态
const verifyingModels = ref<Set<string>>(new Set())
const deletingModels = ref<Set<string>>(new Set())

async function fetchLocalModels() {
  try {
    const res = await fetch(httpUrl('/api/models/local'))
    const data = await res.json()
    console.log('fetchLocalModels response:', data)
    localModels.value = data.models || []
  } catch (e) {
    console.error('Failed to fetch local models:', e)
  }
}

async function fetchAvailableModels() {
  try {
    const res = await fetch(httpUrl('/api/models/available'))
    const data = await res.json()
    availableModels.value = data.models || []
  } catch (e) {
    console.error('Failed to fetch available models:', e)
  }
}

async function downloadModel(modelId: string) {
  if (downloadingModels.value.has(modelId)) return

  downloadingModels.value.add(modelId)
  downloadProgress.value[modelId] = {
    progress: 0,
    downloaded: '0 B',
    total: 'unknown',
    speed: '0 B/s',
  }

  try {
    await fetch(httpUrl('/api/models/download'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_id: modelId,
        use_mirror: appState.useHfMirror,
      }),
    })

    // 轮询下载进度
    const checkProgress = async () => {
      const res = await fetch(httpUrl(`/api/models/progress/${encodeURIComponent(modelId)}`))
      const progress = await res.json()

      if (progress.status === 'downloading') {
        downloadProgress.value[modelId] = {
          progress: progress.progress || 0,
          downloaded: progress.downloaded || '0 B',
          total: progress.total || 'unknown',
          speed: progress.speed || '0 B/s',
          eta: progress.eta || '--:--',
        }
        setTimeout(checkProgress, 1000)
      } else if (progress.status === 'completed') {
        downloadingModels.value.delete(modelId)
        delete downloadProgress.value[modelId]
        await fetchLocalModels()
        await fetchAvailableModels()
      } else if (progress.status === 'failed') {
        downloadingModels.value.delete(modelId)
        delete downloadProgress.value[modelId]
        console.error('Download failed:', progress.error)
      } else {
        setTimeout(checkProgress, 1000)
      }
    }
    setTimeout(checkProgress, 500)
  } catch (e) {
    downloadingModels.value.delete(modelId)
    delete downloadProgress.value[modelId]
    console.error('Failed to start download:', e)
  }
}

function selectModel(modelId: string) {
  console.log('selectModel called with:', modelId)
  console.log('current asrModelId:', appState.asrModelId)
  appState.setAsrModelId(modelId)
  console.log('after set asrModelId:', appState.asrModelId)
}

async function deleteModel(modelId: string) {
  if (deletingModels.value.has(modelId)) return

  deletingModels.value.add(modelId)
  try {
    const res = await fetch(httpUrl(`/api/models/${encodeURIComponent(modelId)}`), {
      method: 'DELETE',
    })
    const data = await res.json()
    if (data.success) {
      message.success(t('settings.asr.deleteSuccess'))
      // 如果删除的是当前选中的模型，清空选择
      if (appState.asrModelId === modelId) {
        appState.setAsrModelId('')
      }
      await fetchLocalModels()
      await fetchAvailableModels()
    } else {
      message.error(data.error || t('settings.asr.deleteFailed'))
    }
  } catch (e) {
    console.error('Failed to delete model:', e)
    message.error(t('settings.asr.deleteFailed'))
  } finally {
    deletingModels.value.delete(modelId)
  }
}

async function verifyModel(modelId: string) {
  if (verifyingModels.value.has(modelId)) return

  verifyingModels.value.add(modelId)
  try {
    const res = await fetch(
      httpUrl(`/api/models/verify/${encodeURIComponent(modelId)}?use_mirror=${appState.useHfMirror}`)
    )
    const data = await res.json()
    if (data.valid) {
      message.success(t('settings.asr.verifySuccess'))
    } else {
      const missing = data.missing?.length || 0
      message.warning(`${t('settings.asr.verifyFailed')} (${missing} files missing)`)
    }
  } catch (e) {
    console.error('Failed to verify model:', e)
    message.error(t('settings.asr.verifyFailed'))
  } finally {
    verifyingModels.value.delete(modelId)
  }
}

onMounted(() => {
  fetchLocalModels()
  fetchAvailableModels()
  fetchLlmModels()
  loadShortcutSettings()
})

// 调试日志相关
const logContainerRef = ref<HTMLElement | null>(null)
const autoScroll = ref(true)
const isLogConnected = ref(false)
let unsubscribeLog: (() => void) | null = null

// 日志级别选项
const logLevelOptions = [
  { value: 'DEBUG', label: 'DEBUG' },
  { value: 'INFO', label: 'INFO' },
  { value: 'WARNING', label: 'WARNING' },
  { value: 'ERROR', label: 'ERROR' },
  { value: 'CRITICAL', label: 'CRITICAL' },
]

// 过滤后的日志
const filteredLogs = computed(() => {
  return appState.logs.filter(log => appState.logLevelFilter.includes(log.level))
})

// 连接日志 WebSocket
function connectLogs() {
  if (isLogConnected.value) return

  unsubscribeLog = logController.onLog((entry) => {
    appState.addLog(entry)
    if (autoScroll.value) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  })

  logController.connect()
  isLogConnected.value = true
}

// 断开日志 WebSocket
function disconnectLogs() {
  if (unsubscribeLog) {
    unsubscribeLog()
    unsubscribeLog = null
  }
  logController.disconnect()
  isLogConnected.value = false
}

// 打开开发者工具
async function openDevTools() {
  await invoke('open_devtools')
}

// 滚动到底部
function scrollToBottom() {
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
}

// 获取日志级别对应的颜色类
function getLogLevelClass(level: string): string {
  const classes: Record<string, string> = {
    DEBUG: 'log-debug',
    INFO: 'log-info',
    WARNING: 'log-warning',
    ERROR: 'log-error',
    CRITICAL: 'log-critical',
  }
  return classes[level] || ''
}

// 双击复制日志条目
async function copyLogEntry(log: { timestamp: string; level: string; logger: string; message: string }) {
  const text = `${log.timestamp} [${log.level}] ${log.logger}: ${log.message}`
  try {
    await navigator.clipboard.writeText(text)
    message.success(t('settings.debug.copied'))
  } catch (e) {
    console.error('Failed to copy log entry:', e)
  }
}

// 监听标签切换，自动连接/断开
watch(activeTab, (newTab) => {
  if (newTab === 'debug' && !isLogConnected.value) {
    connectLogs()
  }
})

onUnmounted(() => {
  disconnectLogs()
})
</script>

<template>
  <div class="settings-panel" :class="{ standalone: props.isStandalone }">
    <!-- 面板头部（支持拖动窗口） -->
    <div class="panel-header" @mousedown="emit('start-drag')">
      <span class="panel-title">{{ t('settings.title') }}</span>
      <button class="close-btn" @click.stop="emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="panel-body">
      <!-- 左侧标签导航 -->
      <div class="tabs-nav">
        <div
          class="tab-item"
          :class="{ active: activeTab === 'general' }"
          @click="activeTab = 'general'"
        >
          <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span>{{ t('settings.tabs.general') }}</span>
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'voice' }"
          @click="activeTab = 'voice'"
        >
          <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
          <span>{{ t('settings.tabs.voice') }}</span>
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'llm' }"
          @click="activeTab = 'llm'"
        >
          <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span>{{ t('settings.tabs.llm') }}</span>
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'asr' }"
          @click="activeTab = 'asr'"
        >
          <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
          <span>{{ t('settings.tabs.asr') }}</span>
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'debug' }"
          @click="activeTab = 'debug'"
        >
          <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            <line x1="8" y1="6" x2="16" y2="6" />
            <line x1="8" y1="10" x2="16" y2="10" />
            <line x1="8" y1="14" x2="12" y2="14" />
          </svg>
          <span>{{ t('settings.tabs.debug') }}</span>
        </div>
      </div>

      <!-- 右侧内容区 -->
      <div class="tab-content">
        <!-- 通用设置 -->
        <div v-show="activeTab === 'general'" class="tab-pane">
          <!-- UI Language -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.uiLanguage') }}</span>
            <a-select
              :value="currentLocale"
              @update:value="onLocaleChange"
              :options="localeOptions"
              size="small"
              class="config-select"
              :dropdown-style="{ background: '#2c2c2e' }"
            />
          </div>

          <!-- Max History -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.maxHistory') }}</span>
            <a-slider
              :value="appState.contextMaxHistory"
              @update:value="appState.setContextMaxHistory"
              :min="5"
              :max="20"
              :step="1"
              class="config-slider"
            />
            <span class="slider-value">{{ appState.contextMaxHistory }}</span>
          </div>

          <!-- Shortcut Settings -->
          <div class="shortcut-section">
            <div class="section-title">{{ t('settings.shortcut.title') }}</div>
            <div class="config-item">
              <span class="config-label">{{ t('settings.shortcut.toggleRecording') }}</span>
              <div class="shortcut-inputs">
                <a-select
                  v-model:value="shortcutModifiers"
                  mode="multiple"
                  :options="modifierOptions"
                  size="small"
                  class="modifier-select"
                  :dropdown-style="{ background: '#2c2c2e' }"
                />
                <span class="shortcut-plus">+</span>
                <a-select
                  v-model:value="shortcutKey"
                  :options="keyOptions"
                  size="small"
                  class="key-select"
                  :dropdown-style="{ background: '#2c2c2e' }"
                />
                <a-button size="small" @click="saveShortcut">
                  {{ t('settings.shortcut.save') }}
                </a-button>
              </div>
            </div>
            <div v-if="shortcutError" class="shortcut-error">{{ shortcutError }}</div>

            <!-- 打开设置快捷键 -->
            <div class="config-item">
              <span class="config-label">{{ t('settings.shortcut.openSettings') }}</span>
              <div class="shortcut-inputs">
                <a-select
                  v-model:value="openSettingsModifiers"
                  mode="multiple"
                  :options="modifierOptions"
                  size="small"
                  class="modifier-select"
                  :dropdown-style="{ background: '#2c2c2e' }"
                />
                <span class="shortcut-plus">+</span>
                <a-select
                  v-model:value="openSettingsKey"
                  :options="keyOptions"
                  size="small"
                  class="key-select"
                  :dropdown-style="{ background: '#2c2c2e' }"
                />
                <a-button size="small" @click="saveOpenSettingsShortcut">
                  {{ t('settings.shortcut.save') }}
                </a-button>
              </div>
            </div>
            <div v-if="openSettingsError" class="shortcut-error">{{ openSettingsError }}</div>
          </div>
        </div>

        <!-- 语音设置 -->
        <div v-show="activeTab === 'voice'" class="tab-pane">
          <!-- ASR Language -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.asrLanguage') }}</span>
            <a-select
              :value="appState.asrLanguage"
              @update:value="appState.setAsrLanguage"
              :disabled="isRecording"
              :options="asrLanguageOptions"
              size="small"
              class="config-select"
              :dropdown-style="{ background: '#2c2c2e' }"
            />
          </div>

          <!-- Output Mode -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.autoInputMode.label') }}</span>
            <a-select
              :value="appState.autoInputMode"
              @update:value="appState.setAutoInputMode"
              :disabled="isRecording"
              :options="autoInputModeOptions"
              size="small"
              class="config-select"
              :dropdown-style="{ background: '#2c2c2e' }"
            />
          </div>

          <!-- Correction -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.correction') }}</span>
            <a-switch
              :checked="appState.correctionEnabled"
              @update:checked="appState.setCorrectionEnabled"
              :disabled="isRecording"
              size="small"
            />
          </div>

          <!-- Context Correction -->
          <div class="config-item" v-if="appState.correctionEnabled">
            <span class="config-label">{{ t('settings.contextCorrection') }}</span>
            <a-switch
              :checked="appState.contextEnabled"
              @update:checked="appState.setContextEnabled"
              :disabled="isRecording"
              size="small"
            />
          </div>

          <!-- Context Count -->
          <div class="config-item" v-if="appState.correctionEnabled && appState.contextEnabled">
            <span class="config-label">{{ t('settings.contextCount') }}</span>
            <a-slider
              :value="appState.contextCount"
              @update:value="appState.setContextCount"
              :disabled="isRecording"
              :min="1"
              :max="10"
              :step="1"
              class="config-slider"
            />
            <span class="slider-value">{{ appState.contextCount }}</span>
          </div>

          <!-- Translate Language -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.translateLanguage') }}</span>
            <a-select
              :value="appState.targetLanguage"
              @update:value="appState.setTargetLanguage"
              :disabled="isRecording"
              :options="translateLanguageOptions"
              size="small"
              class="config-select"
              placeholder="Off"
              :dropdown-style="{ background: '#2c2c2e' }"
            />
          </div>
        </div>

        <!-- LLM 设置 -->
        <div v-show="activeTab === 'llm'" class="tab-pane">
          <!-- API Base -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.llm.apiBase') }}</span>
            <a-input
              :value="appState.llmApiBase"
              @update:value="onApiBaseChange"
              size="small"
              class="config-input"
            />
          </div>

          <!-- API Key -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.llm.apiKey') }}</span>
            <a-input-password
              :value="appState.llmApiKey"
              @update:value="appState.setLlmApiKey"
              size="small"
              class="config-input"
              :placeholder="t('settings.llm.apiKeyPlaceholder')"
            />
          </div>

          <!-- Model -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.llm.model') }}</span>
            <a-auto-complete
              :value="appState.llmModel"
              @update:value="appState.setLlmModel"
              :options="llmModelOptions"
              size="small"
              class="config-input"
              :filter-option="false"
              :dropdown-style="{ background: '#2c2c2e' }"
            />
          </div>

          <!-- Timeout -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.llm.timeout') }}</span>
            <a-input-number
              :value="appState.llmTimeout"
              @update:value="appState.setLlmTimeout"
              size="small"
              :min="1"
              :max="120"
              class="config-number"
            />
          </div>

          <!-- Temperature -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.llm.temperature') }}</span>
            <a-slider
              :value="appState.llmTemperature"
              @update:value="appState.setLlmTemperature"
              :min="0"
              :max="1"
              :step="0.1"
              class="config-slider"
            />
            <span class="slider-value">{{ appState.llmTemperature }}</span>
          </div>
        </div>

        <!-- ASR 设置 -->
        <div v-show="activeTab === 'asr'" class="tab-pane">
          <!-- 当前模型 ID -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.asr.modelPath') }}</span>
            <a-input
              :value="appState.asrModelId"
              @update:value="appState.setAsrModelId"
              size="small"
              class="config-input"
            />
          </div>

          <!-- HuggingFace 镜像开关 -->
          <div class="config-item">
            <span class="config-label">{{ t('settings.asr.useMirror') }}</span>
            <a-switch
              :checked="appState.useHfMirror"
              @update:checked="appState.setUseHfMirror"
              size="small"
            />
            <span class="config-hint">{{ t('settings.asr.useMirrorHint') }}</span>
          </div>

          <!-- 本地模型列表 -->
          <div class="model-section">
            <div class="section-title">{{ t('settings.asr.localModels') }}</div>
            <div class="model-list" v-if="localModels.length > 0">
              <div
                v-for="model in localModels"
                :key="model.id"
                class="model-item local-model"
                :class="{ active: model.id === appState.asrModelId }"
                @click="selectModel(model.id)"
              >
                <div class="model-info">
                  <span class="model-name">{{ model.name }}</span>
                  <span class="model-size">{{ model.size }}</span>
                </div>
                <div class="model-actions" @click.stop>
                  <a-button
                    size="small"
                    :loading="verifyingModels.has(model.id)"
                    @click="verifyModel(model.id)"
                  >
                    {{ verifyingModels.has(model.id) ? t('settings.asr.verifying') : t('settings.asr.verify') }}
                  </a-button>
                  <a-popconfirm
                    :title="t('settings.asr.deleteConfirm')"
                    @confirm="deleteModel(model.id)"
                    :ok-text="t('settings.asr.delete')"
                    cancel-text="Cancel"
                  >
                    <a-button
                      size="small"
                      danger
                      :loading="deletingModels.has(model.id)"
                    >
                      {{ t('settings.asr.delete') }}
                    </a-button>
                  </a-popconfirm>
                </div>
              </div>
            </div>
            <div v-else class="no-models">{{ t('settings.asr.noLocalModels') }}</div>
          </div>

          <!-- 可下载模型 -->
          <div class="model-section">
            <div class="section-title">{{ t('settings.asr.availableModels') }}</div>
            <div class="model-list">
              <div v-for="model in availableModels" :key="model.id" class="model-item downloadable">
                <div class="model-info">
                  <span class="model-name">{{ model.name }}</span>
                  <span class="model-desc">{{ t(`settings.asr.models.${model.id}.description`, model.description) }}</span>
                </div>
                <template v-if="!model.downloaded">
                  <div v-if="downloadingModels.has(model.id)" class="download-progress">
                    <a-progress
                      :percent="downloadProgress[model.id]?.progress || 0"
                      :show-info="false"
                      size="small"
                      :stroke-color="'#4A90E2'"
                    />
                    <div class="progress-info">
                      <span>{{ downloadProgress[model.id]?.downloaded || '0 B' }} / {{ downloadProgress[model.id]?.total || '?' }}</span>
                      <span>{{ downloadProgress[model.id]?.speed || '0 B/s' }} | {{ downloadProgress[model.id]?.eta || '--:--' }}</span>
                    </div>
                  </div>
                  <a-button
                    v-else
                    size="small"
                    @click.stop="downloadModel(model.id)"
                  >
                    {{ t('settings.asr.download') }}
                  </a-button>
                </template>
                <span v-else class="downloaded-badge">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 调试设置 -->
        <div v-show="activeTab === 'debug'" class="tab-pane debug-pane">
          <!-- 控制栏 -->
          <div class="debug-controls">
            <div class="control-left">
              <span class="connection-status" :class="{ connected: isLogConnected }">
                {{ isLogConnected ? t('settings.debug.connected') : t('settings.debug.disconnected') }}
              </span>
            </div>
            <div class="control-right">
              <a-button v-if="!isLogConnected" size="small" @click="connectLogs">
                {{ t('settings.debug.connect') }}
              </a-button>
              <a-button v-else size="small" @click="disconnectLogs">
                {{ t('settings.debug.disconnect') }}
              </a-button>
              <a-button size="small" @click="appState.clearLogs">
                {{ t('settings.debug.clear') }}
              </a-button>
              <a-button size="small" @click="openDevTools">
                {{ t('settings.debug.devtools') }}
              </a-button>
            </div>
          </div>

          <!-- 过滤选项 -->
          <div class="debug-filters">
            <span class="filter-label">{{ t('settings.debug.filterLevel') }}:</span>
            <a-checkbox-group
              :value="appState.logLevelFilter"
              @update:value="appState.setLogLevelFilter"
              :options="logLevelOptions"
              size="small"
            />
            <div class="auto-scroll-toggle">
              <span>{{ t('settings.debug.autoScroll') }}</span>
              <a-switch v-model:checked="autoScroll" size="small" />
            </div>
          </div>

          <!-- 日志列表 -->
          <div ref="logContainerRef" class="log-container">
            <div v-if="filteredLogs.length === 0" class="no-logs">
              {{ t('settings.debug.noLogs') }}
            </div>
            <div
              v-for="(log, index) in filteredLogs"
              :key="index"
              class="log-entry"
              :class="getLogLevelClass(log.level)"
              @dblclick="copyLogEntry(log)"
            >
              <span class="log-time">{{ log.timestamp.split('T')[1]?.split('.')[0] || '' }}</span>
              <span class="log-level">{{ log.level }}</span>
              <span class="log-logger">{{ log.logger }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-panel {
  background: rgba(45, 45, 48, 0.95);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
  position: absolute;
  top: calc(100% + 8px);
  left: 24px;
  z-index: 100;
  width: 540px;
  height: 420px;
  display: flex;
  flex-direction: column;
}

.settings-panel.standalone {
  position: relative;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  min-width: 540px;
  min-height: 420px;
  margin: 0;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  background: rgba(28, 28, 30, 0.85);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.panel-title {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 500;
}

.close-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
}

.close-btn svg {
  width: 14px;
  height: 14px;
}

.panel-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.tabs-nav {
  width: 90px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  padding: 8px;
  flex-shrink: 0;
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 8px;
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
  transition: all 0.2s ease;
  margin-bottom: 4px;
}

.tab-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
}

.tab-item.active {
  background: rgba(74, 144, 226, 0.2);
  color: #4A90E2;
}

.tab-icon {
  width: 18px;
  height: 18px;
}

.tab-content {
  flex: 1;
  padding: 12px 16px;
  overflow-y: auto;
}

.tab-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  min-width: 80px;
  flex-shrink: 0;
}

.config-select {
  width: 140px;
}

.config-input {
  flex: 1;
  max-width: 200px;
}

.config-number {
  width: 80px;
}

.config-slider {
  flex: 1;
  max-width: 120px;
}

.slider-value {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  min-width: 30px;
  text-align: right;
}

.model-section {
  margin-top: 8px;
}

.shortcut-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.shortcut-section .config-item {
  margin-top: 10px;
}

.shortcut-inputs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.modifier-select {
  min-width: 120px;
  max-width: 180px;
}

.key-select {
  width: 70px;
}

.shortcut-plus {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.shortcut-error {
  color: #ff4d4f;
  font-size: 11px;
  margin-top: 6px;
}

.section-title {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.model-item.active {
  background: rgba(74, 144, 226, 0.2);
  border: 1px solid rgba(74, 144, 226, 0.3);
}

.model-item.downloadable {
  cursor: default;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.model-name {
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
}

.model-size {
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
}

.model-desc {
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
}

.downloaded-badge {
  color: #52c41a;
  font-size: 14px;
}

.model-item.local-model {
  flex-wrap: wrap;
  gap: 8px;
}

.model-item.local-model .model-info {
  flex: 1;
  min-width: 100px;
}

.model-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.no-models {
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
  padding: 12px;
  text-align: center;
}

.config-hint {
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
  margin-left: 8px;
}

.download-progress {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 220px;
  width: 220px;
}

.download-progress :deep(.ant-progress) {
  margin: 0;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
  gap: 8px;
}

.progress-info span:first-child {
  min-width: 90px;
}

.progress-info span:last-child {
  min-width: 65px;
  text-align: right;
}

/* Ant Design 深色主题覆盖 */
:deep(.ant-select-selector) {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 6px !important;
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 12px !important;
}

:deep(.ant-select-arrow) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.ant-select-selection-item) {
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 12px !important;
}

:deep(.ant-select-disabled .ant-select-selector) {
  background: rgba(255, 255, 255, 0.04) !important;
  color: rgba(255, 255, 255, 0.3) !important;
}

:deep(.ant-switch) {
  background: rgba(255, 255, 255, 0.15);
  min-width: 36px;
}

:deep(.ant-switch-checked) {
  background: #4A90E2 !important;
}

:deep(.ant-input) {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 6px !important;
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 12px !important;
}

:deep(.ant-input::placeholder) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.ant-input-password) {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 6px !important;
}

:deep(.ant-input-password input) {
  background: transparent !important;
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 12px !important;
}

:deep(.ant-input-password input::placeholder) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.ant-input-password .ant-input-suffix) {
  color: rgba(255, 255, 255, 0.5) !important;
}

:deep(.ant-input-password .ant-input-suffix:hover) {
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.ant-input-number) {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 6px !important;
}

:deep(.ant-input-number-input) {
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 12px !important;
}

:deep(.ant-slider-rail) {
  background: rgba(255, 255, 255, 0.1) !important;
}

:deep(.ant-slider-track) {
  background: #4A90E2 !important;
}

:deep(.ant-slider-handle) {
  border-color: #4A90E2 !important;
}

:deep(.ant-btn) {
  font-size: 11px !important;
}

/* 调试面板样式 */
.debug-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 8px;
}

.debug-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.control-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-right {
  display: flex;
  gap: 6px;
}

.connection-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 77, 79, 0.2);
  color: #ff4d4f;
}

.connection-status.connected {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.debug-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 11px;
}

.filter-label {
  color: rgba(255, 255, 255, 0.6);
}

.auto-scroll-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  color: rgba(255, 255, 255, 0.6);
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  padding: 8px;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  font-size: 11px;
  min-height: 150px;
}

.no-logs {
  color: rgba(255, 255, 255, 0.4);
  text-align: center;
  padding: 20px;
}

.log-entry {
  display: flex;
  gap: 8px;
  padding: 2px 4px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  border-radius: 3px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.log-entry:hover {
  background-color: rgba(255, 255, 255, 0.08);
}

.log-time {
  color: rgba(255, 255, 255, 0.4);
  flex-shrink: 0;
}

.log-level {
  width: 55px;
  flex-shrink: 0;
  font-weight: 500;
}

.log-logger {
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-message {
  color: rgba(255, 255, 255, 0.8);
  word-break: break-all;
}

.log-debug .log-level { color: #8c8c8c; }
.log-info .log-level { color: #1890ff; }
.log-warning .log-level { color: #faad14; }
.log-error .log-level { color: #ff4d4f; }
.log-critical .log-level { color: #ff4d4f; font-weight: bold; }

:deep(.ant-checkbox-group) {
  display: flex;
  gap: 4px;
}

:deep(.ant-checkbox-wrapper) {
  color: rgba(255, 255, 255, 0.7) !important;
  font-size: 11px !important;
}
</style>

<style>
/* 消息提示框深色主题 */
.ant-message .ant-message-notice-content {
  background: rgba(45, 45, 48, 0.95);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  color: rgba(255, 255, 255, 0.9);
}

.ant-message .ant-message-success .anticon {
  color: #52c41a;
}
</style>
