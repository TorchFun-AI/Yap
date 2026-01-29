<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { getCurrentWindow, LogicalSize, LogicalPosition, availableMonitors } from '@tauri-apps/api/window'
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

// 初始化窗口
onMounted(async () => {
  const appWindow = getCurrentWindow()
  const savedPosition = await loadWindowPosition()
  const ballWindowSize = WINDOW_BALL_SIZE + WINDOW_SHADOW * 2

  const { x, y } = await clampToScreen(savedPosition.x, savedPosition.y, ballWindowSize, ballWindowSize)
  await appWindow.setSize(new LogicalSize(ballWindowSize, ballWindowSize))
  await appWindow.setPosition(new LogicalPosition(x, y))
})

const togglePanel = async () => {
  if (isAnimating.value) return
  isAnimating.value = true

  const appWindow = getCurrentWindow()
  const pos = await appWindow.outerPosition()
  const scale = await appWindow.scaleFactor()
  const currentX = pos.x / scale
  const currentY = pos.y / scale

  if (!showPanel.value) {
    // 展开面板
    const totalHeight = WINDOW_PANEL_HEIGHT + WINDOW_GAP + WINDOW_BALL_SIZE + WINDOW_SHADOW * 2
    const totalWidth = WINDOW_PANEL_WIDTH + WINDOW_SHADOW * 2

    // 计算新位置：球保持在右下角
    const newX = currentX - (WINDOW_PANEL_WIDTH - WINDOW_BALL_SIZE)
    const newY = currentY - (WINDOW_PANEL_HEIGHT + WINDOW_GAP)

    const { x, y } = await clampToScreen(newX, newY, totalWidth, totalHeight)

    // 先调整窗口大小和位置
    await appWindow.setSize(new LogicalSize(totalWidth, totalHeight))
    await appWindow.setPosition(new LogicalPosition(x, y))

    // 然后显示面板（触发动画）
    await nextTick()
    showPanel.value = true

    // 保存位置
    await saveWindowPosition(x, y)

    setTimeout(() => {
      isAnimating.value = false
    }, 350)
  } else {
    // 收起面板 - 先播放动画
    showPanel.value = false

    // 等待动画完成后再缩小窗口
    setTimeout(async () => {
      const ballWindowSize = WINDOW_BALL_SIZE + WINDOW_SHADOW * 2

      // 计算球的新位置
      const newX = currentX + (WINDOW_PANEL_WIDTH - WINDOW_BALL_SIZE)
      const newY = currentY + WINDOW_PANEL_HEIGHT + WINDOW_GAP

      await appWindow.setSize(new LogicalSize(ballWindowSize, ballWindowSize))
      await appWindow.setPosition(new LogicalPosition(newX, newY))

      // 保存位置
      await saveWindowPosition(newX, newY)

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
