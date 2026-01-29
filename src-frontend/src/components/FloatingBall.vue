<script setup lang="ts">
import { ref, computed } from 'vue'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { useAppState } from '@/stores/appState'
import { BallIconColorMap, AppStatus, DesignColors } from '@/constants'

const props = defineProps<{
  showPulse?: boolean
}>()

const emit = defineEmits<{
  click: []
}>()

const appState = useAppState()
const startPos = ref({ x: 0, y: 0 })
const moved = ref(false)

const iconColor = computed(() => BallIconColorMap[appState.status] || BallIconColorMap[AppStatus.IDLE])
const isActive = computed(() => appState.isActive)

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
    @mousedown="onMouseDown"
    @mouseup="onMouseUp"
  >
    <!-- Idle: Sparkles 双星闪烁图标 -->
    <svg
      v-if="!isActive"
      class="ball-icon"
      :style="{ color: iconColor }"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M12 3L13.5 8.5L19 10L13.5 11.5L12 17L10.5 11.5L5 10L10.5 8.5L12 3Z" />
      <path d="M19 16L20 18.5L22.5 19.5L20 20.5L19 23L18 20.5L15.5 19.5L18 18.5L19 16Z" />
    </svg>

    <!-- Active: 麦克风图标 -->
    <svg
      v-else
      class="ball-icon"
      :style="{ color: iconColor }"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10v1a7 7 0 0 0 14 0v-1" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>

    <div class="pulse" v-if="isActive && showPulse !== false" :style="{ background: iconColor }" />
  </div>
</template>

<style scoped>
.floating-ball {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  position: relative;
  background: rgba(31, 31, 31, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.floating-ball:hover {
  transform: scale(1.05);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.25);
}

.floating-ball:active {
  cursor: grabbing;
  transform: scale(0.98);
}

.ball-icon {
  width: 24px;
  height: 24px;
  transition: color 0.3s ease;
}

.pulse {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  opacity: 0.4;
  animation: pulse 1.5s ease-out infinite;
  z-index: -1;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 0.4;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}
</style>
