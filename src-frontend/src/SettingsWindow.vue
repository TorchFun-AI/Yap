<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { getCurrentWindow } from '@tauri-apps/api/window'
import SettingsPanel from './components/SettingsPanel.vue'

const appWindow = getCurrentWindow()

// 关闭设置窗口
const closeWindow = async () => {
  try {
    await appWindow.close()
  } catch (e) {
    console.error('Failed to close window:', e)
  }
}

// 开始拖动窗口
const startDrag = async () => {
  try {
    await appWindow.startDragging()
  } catch (e) {
    // 忽略拖动错误
  }
}

// 拦截 Command+W 关闭窗口
const handleKeyDown = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'w') {
    e.preventDefault()
    closeWindow()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <div class="settings-window">
    <SettingsPanel
      :is-standalone="true"
      @close="closeWindow"
      @start-drag="startDrag"
    />
  </div>
</template>

<style scoped>
.settings-window {
  width: 100%;
  height: 100vh;
  background: transparent;
  overflow: visible;
  padding: 16px;
  box-sizing: border-box;
}
</style>
