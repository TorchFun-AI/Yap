<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getCurrentWindow } from '@tauri-apps/api/window'
import SettingsPanel from './components/SettingsPanel.vue'

const appWindow = getCurrentWindow()

// Resize 边缘检测阈值（像素）
const RESIZE_EDGE = 8

// 根据鼠标位置判断 resize 方向
type ResizeDirection = 'north' | 'south' | 'east' | 'west' | 'northEast' | 'northWest' | 'southEast' | 'southWest' | null

function getResizeDirection(e: MouseEvent): ResizeDirection {
  const el = e.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const w = rect.width
  const h = rect.height

  const onLeft = x < RESIZE_EDGE
  const onRight = x > w - RESIZE_EDGE
  const onTop = y < RESIZE_EDGE
  const onBottom = y > h - RESIZE_EDGE

  if (onTop && onLeft) return 'northWest'
  if (onTop && onRight) return 'northEast'
  if (onBottom && onLeft) return 'southWest'
  if (onBottom && onRight) return 'southEast'
  if (onTop) return 'north'
  if (onBottom) return 'south'
  if (onLeft) return 'west'
  if (onRight) return 'east'
  return null
}

// 方向到光标样式的映射
const cursorMap: Record<string, string> = {
  north: 'ns-resize',
  south: 'ns-resize',
  east: 'ew-resize',
  west: 'ew-resize',
  northEast: 'nesw-resize',
  southWest: 'nesw-resize',
  northWest: 'nwse-resize',
  southEast: 'nwse-resize',
}

// 当前光标样式
const currentCursor = ref('default')

// 鼠标移动时更新光标
function handleMouseMove(e: MouseEvent) {
  const dir = getResizeDirection(e)
  currentCursor.value = dir ? cursorMap[dir] : 'default'
}

// 鼠标按下时开始 resize
async function handleMouseDown(e: MouseEvent) {
  const dir = getResizeDirection(e)
  if (dir) {
    e.preventDefault()
    try {
      await appWindow.startResizeDragging(dir)
    } catch (err) {
      // 忽略 resize 错误
    }
  }
}

// 鼠标离开时重置光标
function handleMouseLeave() {
  currentCursor.value = 'default'
}

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
  <div
    class="settings-window"
    :style="{ cursor: currentCursor }"
    @mousemove="handleMouseMove"
    @mousedown="handleMouseDown"
    @mouseleave="handleMouseLeave"
  >
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
