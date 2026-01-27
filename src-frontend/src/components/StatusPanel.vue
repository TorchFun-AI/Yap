<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { CloseOutlined, AudioOutlined, AudioMutedOutlined } from '@ant-design/icons-vue'
import { useAppState } from '@/stores/appState'
import { signalController } from '@/services/signalController'

const emit = defineEmits<{
  close: []
}>()

const panelContentRef = ref<HTMLElement | null>(null)

const appState = useAppState()
const isRecording = computed(() =>
  appState.status === 'listening' || appState.status === 'processing' || appState.status === 'speaking'
)
const bufferDuration = ref(0)

const statusColor = computed(() => {
  switch (appState.status) {
    case 'speaking': return 'orange'
    case 'processing': return 'blue'
    case 'listening': return 'green'
    case 'error': return 'red'
    default: return 'default'
  }
})

const statusText = computed(() => {
  switch (appState.status) {
    case 'speaking': return 'Speaking'
    case 'processing': return 'Transcribing'
    case 'listening': return 'Listening'
    case 'idle': return 'Idle'
    case 'error': return 'Error'
    default: return appState.status
  }
})

onMounted(async () => {
  try {
    await signalController.connect('ws://127.0.0.1:8765/ws/audio')
    signalController.onMessage((data: any) => {
      if (data.type === 'transcription') {
        appState.setTranscript(data.text)
        bufferDuration.value = 0
      } else if (data.type === 'vad') {
        bufferDuration.value = data.buffer_duration || 0
        if (data.is_speech) {
          appState.setStatus('speaking')
        }
      } else if (data.type === 'status') {
        if (data.status === 'recording') {
          appState.setStatus('listening')
        } else if (data.status === 'stopped') {
          appState.setStatus('idle')
        } else if (data.status === 'transcribing') {
          appState.setStatus('processing')
        } else if (data.status === 'speaking') {
          appState.setStatus('speaking')
        }
      } else if (data.type === 'error') {
        appState.setError(data.message)
      }
    })
    appState.setConnected(true)
  } catch {
    appState.setConnected(false)
  }
})

onUnmounted(() => {
  signalController.disconnect()
})

watch(() => appState.currentTranscript, async () => {
  await nextTick()
  if (panelContentRef.value) {
    panelContentRef.value.scrollTop = panelContentRef.value.scrollHeight
  }
})

const toggleRecording = () => {
  if (isRecording.value) {
    signalController.stopRecording()
    // appState.setStatus('idle') // Let the backend confirm stop, or optimistic?
    // User existing code set it to idle.
    appState.setStatus('idle')
  } else {
    signalController.startRecording({ language: 'zh' })
    // Optimistic update to show UI feedback immediately
    appState.setStatus('listening')
  }
}
</script>

<template>
  <div class="status-panel">
    <div class="panel-header">
      <h3>Vocistant</h3>
      <a-button type="text" @click="emit('close')">
        <template #icon>
          <CloseOutlined />
        </template>
      </a-button>
    </div>

    <div class="panel-content" ref="panelContentRef">
      <div class="status-row">
        <span class="label">Status:</span>
        <a-tag :color="statusColor">
          {{ statusText }}
        </a-tag>
        <span v-if="bufferDuration > 0" class="buffer-info">{{ bufferDuration.toFixed(1) }}s</span>
      </div>

      <div class="status-row">
        <span class="label">Connection:</span>
        <a-tag :color="appState.isConnected ? 'success' : 'default'">
          {{ appState.isConnected ? 'Connected' : 'Disconnected' }}
        </a-tag>
      </div>

      <div class="record-control">
        <a-button
          type="primary"
          shape="circle"
          size="large"
          :danger="isRecording"
          :disabled="!appState.isConnected"
          @click="toggleRecording"
        >
          <template #icon>
            <AudioMutedOutlined v-if="isRecording" />
            <AudioOutlined v-else />
          </template>
        </a-button>
        <span class="record-hint">{{ isRecording ? 'Stop' : 'Start' }} Recording</span>
      </div>

      <div class="transcript-area" v-if="appState.currentTranscript">
        <span class="label">Transcript:</span>
        <p>{{ appState.currentTranscript }}</p>
      </div>

      <div class="error-area" v-if="appState.errorMessage">
        <a-alert :message="appState.errorMessage" type="error" show-icon />
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-panel {
  width: 320px;
  height: 100%;
  background: white;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.panel-header h3 { margin: 0; font-size: 16px; }
.panel-content {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}
.status-row { display: flex; align-items: center; margin-bottom: 12px; }
.label { font-weight: 500; margin-right: 8px; color: #666; }
.record-control { display: flex; align-items: center; gap: 12px; margin: 16px 0; }
.record-hint { color: #666; font-size: 14px; }
.buffer-info { margin-left: 8px; color: #999; font-size: 12px; }
.transcript-area { margin-top: 16px; padding-top: 16px; border-top: 1px solid #f0f0f0; }
.transcript-area p { margin: 8px 0 0; color: #333; }
.error-area { margin-top: 16px; }
</style>
