<script setup lang="ts">
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
  overflow: hidden;
}
</style>
