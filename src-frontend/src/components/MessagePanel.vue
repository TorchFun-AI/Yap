<script setup lang="ts">
import { computed, ref } from 'vue'
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

// 是否显示流式转录（说话或转录时都显示）
const isTranscribing = computed(() =>
  (appState.status === 'speaking' || appState.status === 'transcribing') && appState.partialTranscript
)

// 格式化时长显示
function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return ''
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 双击复制到剪贴板
const copiedId = ref<number | null>(null)

async function copyToClipboard(id: number, text: string) {
  await navigator.clipboard.writeText(text)
  copiedId.value = id
  setTimeout(() => {
    copiedId.value = null
  }, 1500)
}
</script>

<template>
  <transition name="messages-slide">
    <div v-show="visible && (recentMessages.length > 0 || isTranscribing)" class="messages-panel">
      <!-- 实时转录显示 -->
      <div v-if="isTranscribing" class="message-item partial-item">
        <span class="message-text partial-text">{{ appState.partialTranscript }}</span>
      </div>
      <!-- 历史消息 -->
      <div
        v-for="msg in recentMessages"
        :key="msg.id"
        class="message-item"
        @dblclick="copyToClipboard(msg.id, msg.text)"
      >
        <div class="message-header">
          <span class="message-text">{{ msg.text }}</span>
          <span v-if="msg.duration" class="message-duration">{{ formatDuration(msg.duration) }}</span>
        </div>
        <span
          v-if="msg.original && msg.original !== msg.text"
          class="message-original"
        >{{ msg.original }}</span>
        <transition name="fade">
          <span v-if="copiedId === msg.id" class="copy-toast">消息已复制</span>
        </transition>
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
  cursor: pointer;
}

.message-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  margin: 0 -6px;
  padding: 6px;
}

.message-item:last-child {
  border-bottom: none;
}

/* 实时转录样式 */
.partial-item {
  background: rgba(41, 121, 255, 0.1);
  border-radius: 6px;
  margin: 0 -6px;
  padding: 6px;
}

.partial-text {
  color: rgba(41, 121, 255, 0.9);
  font-style: italic;
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

/* 复制提示 */
.copy-toast {
  display: block;
  font-size: 10px;
  color: rgba(120, 200, 120, 0.9);
  margin-top: 4px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
