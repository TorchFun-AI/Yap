<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getCurrentWindow, LogicalSize, LogicalPosition } from '@tauri-apps/api/window'
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
let ballPosition = { x: 0, y: 0 }

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

// 初始化窗口位置
onMounted(async () => {
  const appWindow = getCurrentWindow()
  const savedPosition = await loadWindowPosition()
  await appWindow.setPosition(new LogicalPosition(savedPosition.x, savedPosition.y))
})

const togglePanel = async () => {
  const appWindow = getCurrentWindow()

  if (!showPanel.value) {
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    ballPosition = { x: pos.x / scale + WINDOW_SHADOW, y: pos.y / scale + WINDOW_SHADOW }

    // 保存当前球的位置
    await saveWindowPosition(pos.x / scale, pos.y / scale)

    await appWindow.hide()
    showPanel.value = true
    const totalHeight = WINDOW_PANEL_HEIGHT + WINDOW_GAP + WINDOW_BALL_SIZE + WINDOW_SHADOW * 2
    const totalWidth = WINDOW_PANEL_WIDTH + WINDOW_SHADOW * 2
    await appWindow.setSize(new LogicalSize(totalWidth, totalHeight))
    await appWindow.setPosition(new LogicalPosition(
      ballPosition.x - (WINDOW_PANEL_WIDTH - WINDOW_BALL_SIZE) - WINDOW_SHADOW,
      ballPosition.y - (WINDOW_PANEL_HEIGHT + WINDOW_GAP) - WINDOW_SHADOW
    ))
    await appWindow.show()
  } else {
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    const currentX = pos.x / scale
    const currentY = pos.y / scale
    const newBallX = currentX + (WINDOW_PANEL_WIDTH - WINDOW_BALL_SIZE)
    const newBallY = currentY + WINDOW_PANEL_HEIGHT + WINDOW_GAP

    // 保存收起后球的位置
    await saveWindowPosition(newBallX, newBallY)

    await appWindow.hide()
    showPanel.value = false
    await appWindow.setSize(new LogicalSize(WINDOW_BALL_SIZE + WINDOW_SHADOW * 2, WINDOW_BALL_SIZE + WINDOW_SHADOW * 2))
    await appWindow.setPosition(new LogicalPosition(newBallX, newBallY))
    await appWindow.show()
  }
}
</script>

<template>
  <div class="app-container">
    <StatusPanel v-show="showPanel" @close="togglePanel" />
    <div class="ball-wrapper" :class="{ 'no-panel': !showPanel }">
      <FloatingBall @click="togglePanel" :show-pulse="!showPanel" />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  box-sizing: border-box;
  padding: 16px;
}
.ball-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.ball-wrapper.no-panel {
  margin-top: 0;
}
</style>
