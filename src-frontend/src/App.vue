<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getCurrentWindow, availableMonitors } from '@tauri-apps/api/window'
import { invoke } from '@tauri-apps/api/core'
import FloatingBall from './components/FloatingBall.vue'
import StatusPanel from './components/StatusPanel.vue'
import {
  WINDOW_PANEL_WIDTH,
  WINDOW_PANEL_HEIGHT,
  WINDOW_BALL_SIZE,
  WINDOW_GAP,
  WINDOW_SHADOW,
  DEFAULT_WINDOW_POSITION,
} from '@/constants'

const showPanel = ref(false)
const isAnimating = ref(false)

// 球区域的边界（相对于窗口）
const ballBounds = {
  left: WINDOW_PANEL_WIDTH - WINDOW_BALL_SIZE + WINDOW_SHADOW,
  top: WINDOW_PANEL_HEIGHT + WINDOW_GAP + WINDOW_SHADOW,
  right: WINDOW_PANEL_WIDTH + WINDOW_SHADOW,
  bottom: WINDOW_PANEL_HEIGHT + WINDOW_GAP + WINDOW_BALL_SIZE + WINDOW_SHADOW,
}

let pollTimer: number | null = null
let lastIgnoreState = true

// 保存窗口位置到 Tauri store
const saveWindowPosition = async (x: number, y: number) => {
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
      const primary = monitors[0]
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
  if (showPanel.value) return

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

    // 检测是否在球区域内（增加一些边距使点击更容易）
    const padding = 5
    const isInBall = relX >= ballBounds.left - padding &&
                     relX <= ballBounds.right + padding &&
                     relY >= ballBounds.top - padding &&
                     relY <= ballBounds.bottom + padding

    // 只在状态变化时调用 API
    if (isInBall && lastIgnoreState) {
      await invoke('set_ignore_cursor_events', { ignore: false })
      lastIgnoreState = false
    } else if (!isInBall && !lastIgnoreState) {
      await invoke('set_ignore_cursor_events', { ignore: true })
      lastIgnoreState = true
    }
  } catch (e) {
    // 忽略错误，继续轮询
  }
}

const startPolling = () => {
  if (pollTimer) return
  pollTimer = window.setInterval(pollMousePosition, 50)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 初始化窗口 - 固定大小
onMounted(async () => {
  const savedPosition = await loadWindowPosition()

  // 固定窗口大小为展开状态
  const totalHeight = WINDOW_PANEL_HEIGHT + WINDOW_GAP + WINDOW_BALL_SIZE + WINDOW_SHADOW * 2
  const totalWidth = WINDOW_PANEL_WIDTH + WINDOW_SHADOW * 2

  const { x, y } = await clampToScreen(savedPosition.x, savedPosition.y, totalWidth, totalHeight)
  await invoke('set_window_bounds', { x, y, width: totalWidth, height: totalHeight })

  // 初始状态启用鼠标穿透
  await invoke('set_ignore_cursor_events', { ignore: true })
  lastIgnoreState = true

  // 启动轮询
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

const togglePanel = async () => {
  if (isAnimating.value) return
  isAnimating.value = true

  if (!showPanel.value) {
    // 展开面板
    stopPolling()
    await invoke('set_ignore_cursor_events', { ignore: false })
    lastIgnoreState = false
    showPanel.value = true

    // 保存位置
    const appWindow = getCurrentWindow()
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    await saveWindowPosition(pos.x / scale, pos.y / scale)

    setTimeout(() => {
      isAnimating.value = false
    }, 350)
  } else {
    // 收起面板
    showPanel.value = false

    setTimeout(async () => {
      await invoke('set_ignore_cursor_events', { ignore: true })
      lastIgnoreState = true
      startPolling()

      // 保存位置
      const appWindow = getCurrentWindow()
      const pos = await appWindow.outerPosition()
      const scale = await appWindow.scaleFactor()
      await saveWindowPosition(pos.x / scale, pos.y / scale)

      isAnimating.value = false
    }, 300)
  }
}
</script>

<template>
  <div class="app-container">
    <div class="panel-area">
      <transition name="panel-slide">
        <StatusPanel v-show="showPanel" @close="togglePanel" />
      </transition>
    </div>
    <div class="ball-wrapper">
      <FloatingBall @click="togglePanel" :show-pulse="!showPanel" />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  width: 100%;
  height: 100vh;
  box-sizing: border-box;
  padding: 24px;
  overflow: hidden;
}

.panel-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.ball-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
  flex-shrink: 0;
}

/* Panel slide transition - 从下往上展开 */
.panel-slide-enter-active {
  animation: panelSlideIn 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.panel-slide-leave-active {
  animation: panelSlideOut 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes panelSlideIn {
  0% {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes panelSlideOut {
  0% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  100% {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
}
</style>
