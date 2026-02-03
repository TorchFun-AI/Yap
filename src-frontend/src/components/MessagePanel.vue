<script setup lang="ts">
import { computed } from 'vue'
import { useAppState } from '@/stores/appState'

const props = defineProps<{
  visible: boolean
  maxCount?: number
}>()

const appState = useAppState()

// 最近消息记录
const recentMessages = computed(() =>
  appState.messageHistory.slice(0, props.maxCount || 3)
)

// 格式化时长显示
function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return ''
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>

<template>
  <transition name="messages-slide">
    <div v-show="visible && recentMessages.length > 0" class="messages-panel">
      <div
        v-for="msg in recentMessages"
        :key="msg.id"
        class="message-item"
      >
        <div class="message-header">
          <span class="message-text">{{ msg.text }}</span>
          <span v-if="msg.duration" class="message-duration">{{ formatDuration(msg.duration) }}</span>
        </div>
        <span
          v-if="msg.original && msg.original !== msg.text"
          class="message-original"
        >{{ msg.original }}</span>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.messages-panel {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(30, 30, 32, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  max-height: 120px;
  overflow-y: auto;
  z-index: 15;  /* 在操作面板(20)之下，但下拉菜单(100)会在其之上 */
}

.message-item {
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  line-height: 1.4;
}

.message-item:last-child {
  border-bottom: none;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.message-text {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message-duration {
  flex-shrink: 0;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

.message-original {
  display: block;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  text-decoration: line-through;
  word-wrap: break-word;
  white-space: pre-wrap;
  margin-top: 2px;
}

/* 消息面板动画 */
.messages-slide-enter-active {
  animation: messagesSlideIn 0.25s ease-out;
}

.messages-slide-leave-active {
  animation: messagesSlideOut 0.2s ease-in;
}

@keyframes messagesSlideIn {
  0% {
    opacity: 0;
    transform: translateY(-8px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes messagesSlideOut {
  0% {
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateY(-8px);
  }
}
</style>
