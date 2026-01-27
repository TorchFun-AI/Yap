<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { getCurrentWindow, LogicalSize, LogicalPosition } from '@tauri-apps/api/window'
import FloatingBall from './components/FloatingBall.vue'
import StatusPanel from './components/StatusPanel.vue'
import { useAppState } from '@/stores/appState'
import { checkBackendHealth } from '@/services/bridge'

const showPanel = ref(false)
const appState = useAppState()
let healthCheckInterval: number | null = null
let ballPosition = { x: 0, y: 0 }

const togglePanel = async () => {
  const appWindow = getCurrentWindow()
  const panelWidth = 320
  const panelHeight = 220
  const ballSize = 60
  const gap = 8
  const shadow = 16

  if (!showPanel.value) {
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    ballPosition = { x: pos.x / scale + shadow, y: pos.y / scale + shadow }

    await appWindow.hide()
    showPanel.value = true
    const totalHeight = panelHeight + gap + ballSize + shadow * 2
    const totalWidth = panelWidth + shadow * 2
    await appWindow.setSize(new LogicalSize(totalWidth, totalHeight))
    await appWindow.setPosition(new LogicalPosition(
      ballPosition.x - (panelWidth - ballSize) - shadow,
      ballPosition.y - (panelHeight + gap) - shadow
    ))
    await appWindow.show()
  } else {
    const pos = await appWindow.outerPosition()
    const scale = await appWindow.scaleFactor()
    const currentX = pos.x / scale
    const currentY = pos.y / scale
    const newBallX = currentX + (panelWidth - ballSize)
    const newBallY = currentY + panelHeight + gap

    await appWindow.hide()
    showPanel.value = false
    await appWindow.setSize(new LogicalSize(ballSize + shadow * 2, ballSize + shadow * 2))
    await appWindow.setPosition(new LogicalPosition(newBallX, newBallY))
    await appWindow.show()
  }
}

const checkConnection = async () => {
  const isHealthy = await checkBackendHealth()
  appState.setConnected(isHealthy)
}

onMounted(() => {
  checkConnection()
  healthCheckInterval = window.setInterval(checkConnection, 3000)
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
})
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
