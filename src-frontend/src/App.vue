<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getCurrentWindow, availableMonitors } from '@tauri-apps/api/window'
import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import FloatingBallV2 from './components/FloatingBallV2.vue'
import { useAppState } from '@/stores/appState'
import { signalController } from '@/services/signalController'
import { waveformController } from '@/services/waveformController'
import { AppStatus } from '@/constants'
import {
  WS_DEFAULT_URL,
  WS_WAVEFORM_URL,
  ConnectionStatus,
  WsMessageType,
  BackendStatus,
  WINDOW_BALL_SIZE,
  WINDOW_SHADOW,
  DEFAULT_WINDOW_POSITION,
} from '@/constants'
import { setLocale } from '@/i18n'

const appState = useAppState()
const floatingBallRef = ref<InstanceType<typeof FloatingBallV2> | null>(null)
let unlistenSettingsChanged: UnlistenFn | null = null
let unlistenToggleRecording: UnlistenFn | null = null

// 打开设置快捷键处理函数
const handleOpenSettingsShortcut = async (e: KeyboardEvent) => {
  const shortcut = appState.openSettingsShortcut

  // 检查修饰键
  const modifiersMatch = shortcut.modifiers.every(mod => {
    switch (mod) {
      case 'Meta': return e.metaKey
      case 'Ctrl': return e.ctrlKey
      case 'Alt': return e.altKey
      case 'Shift': return e.shiftKey
      default: return false
    }
  })

  // 确保没有额外的修饰键被按下
  const extraModifiers =
    (e.metaKey && !shortcut.modifiers.includes('Meta')) ||
    (e.ctrlKey && !shortcut.modifiers.includes('Ctrl')) ||
    (e.altKey && !shortcut.modifiers.includes('Alt')) ||
    (e.shiftKey && !shortcut.modifiers.includes('Shift'))

  // 检查按键是否匹配
  const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase()

  if (modifiersMatch && !extraModifiers && keyMatch) {
    e.preventDefault()
    try {
      await invoke('open_settings_window')
    } catch (err) {
      console.error('Failed to open settings window:', err)
    }
  }
}

// 球区域的边界（相对于窗口，悬浮球在左上角）
const ballOnlyBounds = {
  left: WINDOW_SHADOW,
  top: WINDOW_SHADOW,
  right: WINDOW_BALL_SIZE + WINDOW_SHADOW,
  bottom: WINDOW_BALL_SIZE + WINDOW_SHADOW,
}

// 展开时的边界（操作面板在悬浮球右侧水平展开）
const expandedBounds = {
  left: WINDOW_SHADOW,
  top: WINDOW_SHADOW,
  right: WINDOW_BALL_SIZE + 200 + WINDOW_SHADOW,
  bottom: WINDOW_BALL_SIZE + WINDOW_SHADOW,
}

// 展开且有下拉菜单时的边界
const expandedWithDropdownBounds = {
  left: WINDOW_SHADOW,
  top: WINDOW_SHADOW,
  right: WINDOW_BALL_SIZE + 200 + WINDOW_SHADOW,
  bottom: WINDOW_BALL_SIZE + WINDOW_SHADOW + 110,
}

// 展开且有消息记录时的边界
const expandedWithMessagesBounds = {
  left: WINDOW_SHADOW,
  top: WINDOW_SHADOW,
  right: WINDOW_BALL_SIZE + 200 + WINDOW_SHADOW,
  bottom: WINDOW_BALL_SIZE + WINDOW_SHADOW + 140,
}

let pollTimer: number | null = null
let lastIgnoreState = true

// 保存窗口位置到 Tauri store (保留供后续使用)
// @ts-expect-error 暂未使用
const _saveWindowPosition = async (x: number, y: number) => {
  try {
    await invoke('save_window_position', { x, y })
  } catch (e) {
    console.error('Failed to save window position:', e)
  }
}

// 从 Tauri store 加载窗口位置
const loadWindowPosition = async (): Promise<{ x: number; y: number }> => {
  try {
    const pos = await invoke<{ x: number; y: number }>('load_window_position')
    return pos
  } catch {
    return DEFAULT_WINDOW_POSITION
  }
}

// 检查并修正位置到屏幕范围内
const clampToScreen = async (x: number, y: number, width: number, height: number) => {
  try {
    const monitors = await availableMonitors()
    if (monitors.length > 0) {
      const primary = monitors[0]!
      const screenWidth = primary.size.width / primary.scaleFactor
      const screenHeight = primary.size.height / primary.scaleFactor
      if (x < 0 || x + width > screenWidth) {
        x = Math.max(0, Math.min(x, screenWidth - width - 20))
      }
      if (y < 0 || y + height > screenHeight) {
        y = Math.max(0, Math.min(y, screenHeight - height - 20))
      }
    }
  } catch (e) {
    console.error('Failed to get monitors:', e)
  }
  return { x, y }
}

// 轮询检测鼠标位置
const pollMousePosition = async () => {
  try {
    const appWindow = getCurrentWindow()
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    const windowX = pos.x / scale
    const windowY = pos.y / scale

    // 使用 Rust 命令获取全局鼠标位置
    const cursorPos = await invoke<{ x: number; y: number }>('get_cursor_position')
    const cursorX = cursorPos.x
    const cursorY = cursorPos.y

    // 计算鼠标相对于窗口的位置
    const relX = cursorX - windowX
    const relY = cursorY - windowY

    // 根据展开状态和下拉菜单状态选择检测区域
    const isExpanded = floatingBallRef.value?.isExpanded ?? false
    const hasDropdown = floatingBallRef.value?.hasDropdown ?? false
    const hasMessages = floatingBallRef.value?.hasMessages ?? false

    let bounds = ballOnlyBounds
    if (isExpanded && hasDropdown) {
      bounds = expandedWithDropdownBounds
    } else if (isExpanded && hasMessages) {
      bounds = expandedWithMessagesBounds
    } else if (isExpanded) {
      bounds = expandedBounds
    }

    // 检测是否在区域内（增加一些边距使点击更容易）
    const padding = 5
    const isInBounds = relX >= bounds.left - padding &&
                       relX <= bounds.right + padding &&
                       relY >= bounds.top - padding &&
                       relY <= bounds.bottom + padding

    // 只在状态变化时调用 API
    if (isInBounds && lastIgnoreState) {
      await invoke('set_ignore_cursor_events', { ignore: false })
      lastIgnoreState = false
      // 进入窗口范围时自动获取焦点
      await appWindow.setFocus()
      // 窗口可接收事件，停止轮询
      stopPolling()
    } else if (!isInBounds && !lastIgnoreState) {
      await invoke('set_ignore_cursor_events', { ignore: true })
      lastIgnoreState = true
    }
  } catch (e) {
    // 忽略错误，继续轮询
  }
}

const startPolling = () => {
  if (pollTimer) return
  pollTimer = window.setInterval(pollMousePosition, 100)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 录音控制
const toggleRecording = () => {
  // 检查是否可以切换录音（与按钮禁用逻辑一致）
  const isDisabled = appState.status === AppStatus.STARTING || !appState.isConnected
  if (isDisabled) return

  if (appState.isActive) {
    signalController.stopRecording()
    appState.setStatus(AppStatus.IDLE)
  } else {
    signalController.startRecording({
      language: appState.asrLanguage,
      correctionEnabled: appState.correctionEnabled,
      targetLanguage: appState.targetLanguage || undefined,
      asrModelPath: appState.asrModelPath || undefined,
      // LLM 配置
      llmApiKey: appState.llmApiKey || undefined,
      llmApiBase: appState.llmApiBase || undefined,
      llmModel: appState.llmModel,
      llmTimeout: appState.llmTimeout,
      llmTemperature: appState.llmTemperature,
    })
    appState.setStatus(AppStatus.STARTING)
  }
}

// 处理操作区事件
const handleAction = async (id: string, _value?: string) => {
  if (id === 'record') {
    toggleRecording()
  } else if (id === 'settings') {
    try {
      await invoke('open_settings_window')
    } catch (e) {
      console.error('Failed to open settings window:', e)
    }
  }
}

// 初始化窗口 - 固定大小
onMounted(async () => {
  // 监听打开设置快捷键
  document.addEventListener('keydown', handleOpenSettingsShortcut)

  // 监听快捷键触发的录音切换事件
  unlistenToggleRecording = await listen('toggle_recording', () => {
    toggleRecording()
  })

  // 监听设置变更事件（实时同步）
  unlistenSettingsChanged = await listen('settings-changed', () => {
    appState.reloadFromStorage()
    // 重新加载界面语言
    const savedLocale = localStorage.getItem('app-locale') as 'zh' | 'en' | null
    if (savedLocale) {
      setLocale(savedLocale)
    }
  })

  const savedPosition = await loadWindowPosition()

  // 窗口大小：悬浮球 + 操作面板 + 下拉菜单/消息面板空间
  const totalWidth = WINDOW_BALL_SIZE + 200 + WINDOW_SHADOW * 2
  const totalHeight = WINDOW_BALL_SIZE + WINDOW_SHADOW * 2 + 150

  const { x, y } = await clampToScreen(savedPosition.x, savedPosition.y, totalWidth, totalHeight)
  await invoke('set_window_bounds', { x, y, width: totalWidth, height: totalHeight })

  // 初始状态启用鼠标穿透
  await invoke('set_ignore_cursor_events', { ignore: true })
  lastIgnoreState = true

  // 监听鼠标移动，检测是否离开可见区域
  document.addEventListener('mousemove', (e) => {
    if (lastIgnoreState) return

    // 获取当前边界
    const isExpanded = floatingBallRef.value?.isExpanded ?? false
    const hasDropdown = floatingBallRef.value?.hasDropdown ?? false
    const hasMessages = floatingBallRef.value?.hasMessages ?? false

    let bounds = ballOnlyBounds
    if (isExpanded && hasDropdown) {
      bounds = expandedWithDropdownBounds
    } else if (isExpanded && hasMessages) {
      bounds = expandedWithMessagesBounds
    } else if (isExpanded) {
      bounds = expandedBounds
    }

    // 检测鼠标是否在可见区域内
    const padding = 5
    const isInBounds = e.clientX >= bounds.left - padding &&
                       e.clientX <= bounds.right + padding &&
                       e.clientY >= bounds.top - padding &&
                       e.clientY <= bounds.bottom + padding

    if (!isInBounds) {
      invoke('set_ignore_cursor_events', { ignore: true })
      lastIgnoreState = true
      startPolling()
    }
  })

  // 监听窗口失去焦点，重新启动轮询（备份机制）
  window.addEventListener('blur', () => {
    if (!lastIgnoreState) {
      invoke('set_ignore_cursor_events', { ignore: true })
      lastIgnoreState = true
    }
    startPolling()
  })

  // 初始启动轮询（窗口初始无焦点）
  startPolling()

  // 初始化 WebSocket 连接
  signalController.onConnectionStatusChange((status, retry) => {
    appState.setConnectionStatus(status, retry)
    if (status === ConnectionStatus.CONNECTED) {
      appState.setStatus(AppStatus.IDLE)
    }
  })

  signalController.onMessage((data: any) => {
    if (data.type === WsMessageType.TRANSCRIPTION) {
      // 识别完成：添加到历史记录（text 和 original 都是原始文本）
      appState.setTranscript(data.text)
      appState.addToHistory(data.text, data.text, data.audio_duration)
    } else if (data.type === WsMessageType.CORRECTION) {
      // 校正完成：只更新 text，保留 original
      appState.setTranscript(data.text, data.original_text)
      appState.updateLatestHistory(data.text)
    } else if (data.type === WsMessageType.VAD) {
      if (data.is_speech) {
        appState.setStatus(AppStatus.SPEAKING)
      }
    } else if (data.type === WsMessageType.STATUS) {
      if (data.status === BackendStatus.STARTING) {
        appState.setStatus(AppStatus.STARTING)
      } else if (data.status === BackendStatus.RECORDING) {
        appState.setStatus(AppStatus.LISTENING)
      } else if (data.status === BackendStatus.STOPPED) {
        appState.setStatus(AppStatus.IDLE)
      } else if (data.status === BackendStatus.TRANSCRIBING) {
        appState.setStatus(AppStatus.TRANSCRIBING)
      } else if (data.status === BackendStatus.CORRECTING) {
        appState.setStatus(AppStatus.CORRECTING)
      } else if (data.status === BackendStatus.TRANSLATING) {
        appState.setStatus(AppStatus.TRANSLATING)
      } else if (data.status === BackendStatus.SPEAKING) {
        appState.setStatus(AppStatus.SPEAKING)
      }
    } else if (data.type === WsMessageType.ERROR) {
      appState.setError(data.message)
    }
  })

  const wsUrl = import.meta.env.VITE_WS_URL || WS_DEFAULT_URL
  signalController.connect(wsUrl)

  // 初始化波形 WebSocket 连接
  const waveformUrl = import.meta.env.VITE_WS_WAVEFORM_URL || WS_WAVEFORM_URL
  waveformController.onData((levels) => {
    appState.setWaveformLevels(levels)
  })
  waveformController.connect(waveformUrl)
})

onUnmounted(() => {
  // 移除打开设置快捷键监听
  document.removeEventListener('keydown', handleOpenSettingsShortcut)

  if (unlistenToggleRecording) {
    unlistenToggleRecording()
  }
  if (unlistenSettingsChanged) {
    unlistenSettingsChanged()
  }
  stopPolling()
  signalController.disconnect()
  waveformController.disconnect()
  appState.resetWaveformLevels()
})
</script>

<template>
  <div class="app-container">
    <div class="ball-wrapper">
      <FloatingBallV2 ref="floatingBallRef" @action="handleAction" />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  width: 100%;
  height: 100vh;
  box-sizing: border-box;
  padding: 24px;
  overflow: hidden;
}

.ball-wrapper {
  display: flex;
  justify-content: flex-start;
  flex-shrink: 0;
  position: relative;
}
</style>
