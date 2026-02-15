<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { getCurrentWindow, availableMonitors } from '@tauri-apps/api/window'
import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import FloatingBallV2 from './components/FloatingBallV2.vue'
import { useAppState } from '@/stores/appState'
import { signalController } from '@/services/signalController'
import { waveformController } from '@/services/waveformController'
import { initPort, wsUrl } from '@/services/portService'
import { AppStatus } from '@/constants'
import {
  ConnectionStatus,
  WsMessageType,
  BackendStatus,
  WINDOW_BALL_SIZE,
  WINDOW_SHADOW,
  DEFAULT_WINDOW_POSITION,
} from '@/constants'
import { setLocale } from '@/i18n'

const PANEL_WIDTH = 200  // 操作面板宽度

const appState = useAppState()
const floatingBallRef = ref<InstanceType<typeof FloatingBallV2> | null>(null)
const expandDirection = ref<'left' | 'right'>('right')
let unlistenSettingsChanged: UnlistenFn | null = null
let unlistenToggleRecording: UnlistenFn | null = null

// 关闭设置窗口快捷键处理函数 (Command+W / Ctrl+W)
const handleCloseSettingsShortcut = async (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'w') {
    e.preventDefault()
    try {
      await invoke('close_settings_window')
    } catch (err) {
      // 忽略错误（设置窗口可能未打开）
    }
  }
}

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

// 球区域的边界（相对于窗口，悬浮球在窗口中间）
const getBallOnlyBounds = () => {
  return {
    left: WINDOW_SHADOW + PANEL_WIDTH,
    top: WINDOW_SHADOW,
    right: WINDOW_SHADOW + PANEL_WIDTH + WINDOW_BALL_SIZE,
    bottom: WINDOW_BALL_SIZE + WINDOW_SHADOW,
  }
}

// 展开时的边界（操作面板展开）
const getExpandedBounds = () => {
  if (expandDirection.value === 'left') {
    // 左侧展开：操作面板在悬浮球左侧
    return {
      left: WINDOW_SHADOW,
      top: WINDOW_SHADOW,
      right: WINDOW_SHADOW + PANEL_WIDTH + WINDOW_BALL_SIZE,
      bottom: WINDOW_BALL_SIZE + WINDOW_SHADOW,
    }
  }
  // 右侧展开：操作面板在悬浮球右侧
  return {
    left: WINDOW_SHADOW + PANEL_WIDTH,
    top: WINDOW_SHADOW,
    right: WINDOW_SHADOW + PANEL_WIDTH + WINDOW_BALL_SIZE + PANEL_WIDTH,
    bottom: WINDOW_BALL_SIZE + WINDOW_SHADOW,
  }
}

// 展开且有下拉菜单时的边界
const getExpandedWithDropdownBounds = () => {
  const base = getExpandedBounds()
  return {
    ...base,
    bottom: base.bottom + 110,
  }
}

// 展开且有消息记录时的边界
const getExpandedWithMessagesBounds = () => {
  const base = getExpandedBounds()
  return {
    ...base,
    bottom: base.bottom + 140,
  }
}

let pollTimer: number | null = null
let lastIgnoreState = true

const WINDOW_POSITION_KEY = 'app-window-position'

// 保存窗口位置到 localStorage
const saveWindowPosition = (x: number, y: number) => {
  localStorage.setItem(WINDOW_POSITION_KEY, JSON.stringify({ x, y }))
}

// 从 localStorage 加载窗口位置
const loadWindowPosition = (): { x: number; y: number } | null => {
  try {
    const saved = localStorage.getItem(WINDOW_POSITION_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch {
    // ignore
  }
  return null
}

// 校验悬浮球位置，无保存位置或超出屏幕时使用默认位置（屏幕 75%/75%）
const getValidBallPosition = async (saved: { x: number; y: number } | null) => {
  try {
    const monitors = await availableMonitors()
    if (monitors.length > 0) {
      const primary = monitors[0]!
      const screenWidth = primary.size.width / primary.scaleFactor
      const screenHeight = primary.size.height / primary.scaleFactor

      const defaultPos = () => ({
        x: Math.min(screenWidth * 0.75, screenWidth - WINDOW_BALL_SIZE),
        y: Math.min(screenHeight * 0.75, screenHeight - WINDOW_BALL_SIZE),
      })

      if (!saved) {
        return defaultPos()
      }

      // 只检查悬浮球本身是否超出屏幕（收缩状态）
      const isOutOfBounds = saved.x < 0 || saved.y < 0 ||
        saved.x + WINDOW_BALL_SIZE > screenWidth ||
        saved.y + WINDOW_BALL_SIZE > screenHeight

      if (isOutOfBounds) {
        return defaultPos()
      }

      return saved
    }
  } catch (e) {
    console.error('Failed to validate window position:', e)
  }
  return saved ?? DEFAULT_WINDOW_POSITION
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

    let bounds = getBallOnlyBounds()
    if (isExpanded && hasDropdown) {
      bounds = getExpandedWithDropdownBounds()
    } else if (isExpanded && hasMessages) {
      bounds = getExpandedWithMessagesBounds()
    } else if (isExpanded) {
      bounds = getExpandedBounds()
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

// 更新展开方向（方向改变时先收起面板再展开）
const updateExpandDirection = async () => {
  try {
    const appWindow = getCurrentWindow()
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    const monitors = await availableMonitors()

    if (monitors.length > 0) {
      const primary = monitors[0]!
      const screenWidth = primary.size.width / primary.scaleFactor
      const windowX = pos.x / scale

      // 计算悬浮球中心在屏幕上的位置（悬浮球在窗口中间）
      const ballCenterX = windowX + WINDOW_SHADOW + PANEL_WIDTH + WINDOW_BALL_SIZE / 2
      const newDirection = ballCenterX > screenWidth / 2 ? 'left' : 'right'

      // 如果方向改变且面板已展开，先收起再展开
      if (newDirection !== expandDirection.value && floatingBallRef.value?.isExpanded) {
        floatingBallRef.value.isExpanded = false
        await new Promise(resolve => setTimeout(resolve, 200)) // 等待收起动画
        expandDirection.value = newDirection
        await new Promise(resolve => setTimeout(resolve, 50))
        floatingBallRef.value.isExpanded = true
      } else {
        expandDirection.value = newDirection
      }
    }
  } catch (e) {
    console.error('Failed to update expand direction:', e)
  }
}

// 处理拖动结束
const handleDragEnd = async () => {
  // 延迟等待拖动完成
  await new Promise(resolve => setTimeout(resolve, 100))

  // 保存窗口位置
  try {
    const appWindow = getCurrentWindow()
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    const windowX = pos.x / scale
    const windowY = pos.y / scale
    // 反算悬浮球在屏幕上的位置（与 onMounted 中的计算互逆）
    const ballX = windowX + WINDOW_SHADOW + PANEL_WIDTH
    const ballY = windowY + WINDOW_SHADOW
    saveWindowPosition(ballX, ballY)
  } catch (e) {
    console.error('Failed to save window position after drag:', e)
  }

  // 更新展开方向
  updateExpandDirection()
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
      asrModelId: appState.asrModelId || undefined,
      // LLM 配置
      llmApiKey: appState.llmApiKey || undefined,
      llmApiBase: appState.llmApiBase || undefined,
      llmModel: appState.llmModel,
      llmTimeout: appState.llmTimeout,
      llmTemperature: appState.llmTemperature,
      // 输出方式
      autoInputMode: appState.autoInputMode,
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
  // 初始化后端端口（必须在 WebSocket 连接之前）
  await initPort()

  // 监听打开设置快捷键
  document.addEventListener('keydown', handleOpenSettingsShortcut)
  // 监听关闭设置窗口快捷键 (Command+W / Ctrl+W)
  document.addEventListener('keydown', handleCloseSettingsShortcut)

  // 监听快捷键触发的录音切换事件
  unlistenToggleRecording = await listen('toggle_recording', () => {
    toggleRecording()
  })

  // 监听设置变更事件（实时同步）
  unlistenSettingsChanged = await listen<Record<string, any>>('settings-changed', (event) => {
    // 从事件数据中获取设置值，避免 localStorage 缓存问题
    if (event.payload && Object.keys(event.payload).length > 0) {
      appState.applySettings(event.payload)
    } else {
      // 兼容旧版本：如果没有传递设置值，从 localStorage 读取
      appState.reloadFromStorage()
    }
    // 重新加载界面语言
    const savedLocale = localStorage.getItem('app-locale') as 'zh' | 'en' | null
    if (savedLocale) {
      setLocale(savedLocale)
    }
  })

  const ballPos = await getValidBallPosition(loadWindowPosition())

  // 窗口大小：两侧操作面板空间 + 悬浮球 + 阴影
  const totalWidth = PANEL_WIDTH + WINDOW_BALL_SIZE + PANEL_WIDTH + WINDOW_SHADOW * 2
  const totalHeight = WINDOW_BALL_SIZE + WINDOW_SHADOW * 2 + 150

  // 计算初始展开方向
  const monitors = await availableMonitors()
  if (monitors.length > 0) {
    const primary = monitors[0]!
    const screenWidth = primary.size.width / primary.scaleFactor
    // 保存的位置是悬浮球在屏幕上的位置
    const ballCenterX = ballPos.x + WINDOW_BALL_SIZE / 2
    expandDirection.value = ballCenterX > screenWidth / 2 ? 'left' : 'right'
  }

  // 窗口位置 = 悬浮球位置 - 悬浮球在窗口中的偏移
  // 悬浮球在窗口中的位置：WINDOW_SHADOW + PANEL_WIDTH
  const windowX = ballPos.x - WINDOW_SHADOW - PANEL_WIDTH
  const windowY = ballPos.y - WINDOW_SHADOW

  await invoke('set_window_bounds', { x: windowX, y: windowY, width: totalWidth, height: totalHeight })

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

    let bounds = getBallOnlyBounds()
    if (isExpanded && hasDropdown) {
      bounds = getExpandedWithDropdownBounds()
    } else if (isExpanded && hasMessages) {
      bounds = getExpandedWithMessagesBounds()
    } else if (isExpanded) {
      bounds = getExpandedBounds()
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
    if (data.type === WsMessageType.TRANSCRIPTION_PARTIAL) {
      // 流式转录：实时更新部分结果
      appState.setPartialTranscript(data.text)
    } else if (data.type === WsMessageType.TRANSCRIPTION) {
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
      } else if (data.status === BackendStatus.DOWNLOADING) {
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
      } else if (data.status === 'error') {
        appState.setError(data.message || 'Unknown error')
      }
    } else if (data.type === WsMessageType.ERROR) {
      appState.setError(data.message)
    } else if (data.type === WsMessageType.TEXT_INPUT_REQUEST) {
      // Tauri 端输入请求
      if (data.text) {
        invoke('input_text', { text: data.text, typewriter: data.typewriter ?? true })
      }
    } else if (data.type === WsMessageType.CLIPBOARD_REQUEST) {
      // Tauri 端剪贴板请求
      if (data.text) {
        invoke('copy_to_clipboard', { text: data.text })
      }
    }
  })

  signalController.connect(wsUrl('/ws/audio'))

  // 初始化波形 WebSocket 连接
  waveformController.onData((levels) => {
    appState.setWaveformLevels(levels)
  })
  waveformController.connect(wsUrl('/ws/waveform'))

  // 启动时自动展开操作区（带动画）
  nextTick(() => {
    if (floatingBallRef.value) {
      floatingBallRef.value.isExpanded = true
    }
  })
})

onUnmounted(() => {
  // 移除打开设置快捷键监听
  document.removeEventListener('keydown', handleOpenSettingsShortcut)
  // 移除关闭设置窗口快捷键监听
  document.removeEventListener('keydown', handleCloseSettingsShortcut)

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
      <FloatingBallV2
        ref="floatingBallRef"
        :expand-direction="expandDirection"
        @action="handleAction"
        @drag="handleDragEnd"
      />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  width: 100%;
  height: 100vh;
  box-sizing: border-box;
  padding: 24px;
  overflow: visible;
}

.ball-wrapper {
  display: flex;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}
</style>
