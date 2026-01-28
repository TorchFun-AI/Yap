<script setup lang="ts">
import { ref, computed } from 'vue'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { useAppState } from '@/stores/appState'
import { BallColorMap, AppStatus } from '@/constants'

const props = defineProps<{
  showPulse?: boolean
}>()

const emit = defineEmits<{
  click: []
}>()

const appState = useAppState()
const startPos = ref({ x: 0, y: 0 })
const moved = ref(false)

const statusColor = computed(() => BallColorMap[appState.status] || BallColorMap[AppStatus.IDLE])

const onMouseDown = (e: MouseEvent) => {
  startPos.value = { x: e.screenX, y: e.screenY }
  moved.value = false
  getCurrentWindow().startDragging()
}

const onMouseUp = (e: MouseEvent) => {
  const dx = Math.abs(e.screenX - startPos.value.x)
  const dy = Math.abs(e.screenY - startPos.value.y)
  if (dx < 5 && dy < 5) {
    emit('click')
  }
}
</script>

<template>
  <div
    class="floating-ball"
    :style="{ backgroundColor: statusColor }"
    @mousedown="onMouseDown"
    @mouseup="onMouseUp"
  >
    <span class="icon">🎤</span>
    <div class="pulse" v-if="appState.isActive && showPulse !== false" />
  </div>
</template>

<style scoped>
.floating-ball {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  user-select: none;
  position: relative;
}

.floating-ball:active {
  cursor: grabbing;
}

.pulse {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: inherit;
  animation: pulse 1.5s ease-out infinite;
  z-index: -1;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 0.5;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}
</style>
