<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { AudioOutlined, AudioMutedOutlined } from '@ant-design/icons-vue'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { useAppState } from '@/stores/appState'
import { signalController } from '@/services/signalController'
import {
  WS_DEFAULT_URL,
  ConnectionStatus,
  AppStatus,
  WsMessageType,
  BackendStatus,
  StatusColorMap,
  StatusTextMap,
  TRANSLATE_LANGUAGES,
  ASR_LANGUAGES,
  DesignColors,
} from '@/constants'

const emit = defineEmits<{
  close: []
}>()

const panelContentRef = ref<HTMLElement | null>(null)

const appState = useAppState()
const isRecording = computed(() =>
  appState.status === AppStatus.STARTING ||
  appState.status === AppStatus.LISTENING ||
  appState.status === AppStatus.TRANSCRIBING ||
  appState.status === AppStatus.CORRECTING ||
  appState.status === AppStatus.TRANSLATING ||
  appState.status === AppStatus.SPEAKING
)
const bufferDuration = ref(0)
let unlistenShortcut: UnlistenFn | null = null

const statusText = computed(() => StatusTextMap[appState.status] || appState.status)

const connectionText = computed(() => {
  if (appState.connectionStatus === ConnectionStatus.RECONNECTING) {
    return `Reconnecting (${appState.retryCount})...`
  }
  if (appState.connectionStatus === ConnectionStatus.CONNECTED) {
    return 'Connected'
  }
  if (appState.connectionStatus === ConnectionStatus.CONNECTING) {
    return 'Connecting...'
  }
  return 'Disconnected'
})

const isConnected = computed(() => appState.connectionStatus === ConnectionStatus.CONNECTED)

onMounted(async () => {
  unlistenShortcut = await listen('toggle_recording', () => {
    if (appState.isConnected) {
      toggleRecording()
    }
  })

  signalController.onConnectionStatusChange((status, retry) => {
    const prevStatus = appState.connectionStatus
    appState.setConnectionStatus(status, retry)

    if (status === ConnectionStatus.CONNECTED &&
        (prevStatus === ConnectionStatus.RECONNECTING || prevStatus === ConnectionStatus.DISCONNECTED)) {
      appState.setStatus(AppStatus.IDLE)
      bufferDuration.value = 0
    }
  })

  signalController.onMessage((data: any) => {
    if (data.type === WsMessageType.TRANSCRIPTION || data.type === WsMessageType.CORRECTION) {
      appState.setTranscript(data.text, data.original_text)
      bufferDuration.value = 0
    } else if (data.type === WsMessageType.VAD) {
      bufferDuration.value = data.buffer_duration || 0
      if (data.is_speech) {
        appState.setStatus(AppStatus.SPEAKING)
      }
    } else if (data.type === WsMessageType.STATUS) {
      if (data.status === BackendStatus.STARTING) {
        appState.setStatus(AppStatus.STARTING)
      } else if (data.status === BackendStatus.RECORDING) {
        appState.setStatus(AppStatus.LISTENING)
      } else if (data.status === BackendStatus.STOPPED) {
        appState.setStatus(AppStatus.IDLE)
      } else if (data.status === BackendStatus.TRANSCRIBING) {
        appState.setStatus(AppStatus.TRANSCRIBING)
      } else if (data.status === BackendStatus.CORRECTING) {
        appState.setStatus(AppStatus.CORRECTING)
      } else if (data.status === BackendStatus.TRANSLATING) {
        appState.setStatus(AppStatus.TRANSLATING)
      } else if (data.status === BackendStatus.SPEAKING) {
        appState.setStatus(AppStatus.SPEAKING)
      }
    } else if (data.type === WsMessageType.ERROR) {
      appState.setError(data.message)
    }
  })

  const wsUrl = import.meta.env.VITE_WS_URL || WS_DEFAULT_URL
  signalController.connect(wsUrl)
})

onUnmounted(() => {
  unlistenShortcut?.()
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
    appState.setStatus(AppStatus.IDLE)
  } else {
    signalController.startRecording({
      language: appState.asrLanguage,
      correctionEnabled: appState.correctionEnabled,
      targetLanguage: appState.targetLanguage || undefined,
    })
    appState.setStatus(AppStatus.STARTING)
  }
}
</script>

<template>
  <div class="status-panel">
    <!-- Action Bar -->
    <div class="action-bar">
      <div class="action-bar-left">
        <span class="status-indicator" :class="{ connected: isConnected }" />
        <span class="status-text">{{ connectionText }}</span>
        <span class="status-divider">|</span>
        <span class="status-text">{{ statusText }}</span>
        <span v-if="bufferDuration > 0" class="buffer-info">{{ bufferDuration.toFixed(1) }}s</span>
      </div>
      <button
        class="mic-button"
        :class="{ active: isRecording }"
        :disabled="!appState.isConnected"
        @click="toggleRecording"
      >
        <AudioMutedOutlined v-if="isRecording" />
        <AudioOutlined v-else />
      </button>
    </div>

    <!-- Panel Content -->
    <div class="panel-content" ref="panelContentRef">

      <!-- Config Section -->
      <div class="section config-section">
        <div class="config-item">
          <svg class="config-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10" />
            <path d="M2 12h20" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
          <span class="config-label">Language</span>
          <a-select
            :value="appState.asrLanguage"
            @update:value="appState.setAsrLanguage"
            :disabled="isRecording"
            :options="ASR_LANGUAGES"
            size="small"
            class="config-select"
            :dropdown-style="{ background: '#2c2c2e' }"
          />
        </div>

        <div class="config-item">
          <svg class="config-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
          </svg>
          <span class="config-label">Correction</span>
          <a-switch
            :checked="appState.correctionEnabled"
            @update:checked="appState.setCorrectionEnabled"
            :disabled="isRecording"
            size="small"
          />
        </div>

        <div class="config-item">
          <svg class="config-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M5 8l6 6" />
            <path d="M4 14l6-6 2-3" />
            <path d="M2 5h12" />
            <path d="M7 2h1" />
            <path d="M22 22l-5-10-5 10" />
            <path d="M14 18h6" />
          </svg>
          <span class="config-label">Translate</span>
          <a-select
            :value="appState.targetLanguage"
            @update:value="appState.setTargetLanguage"
            :disabled="isRecording"
            :options="TRANSLATE_LANGUAGES"
            size="small"
            class="config-select"
            placeholder="Off"
            :dropdown-style="{ background: '#2c2c2e' }"
          />
        </div>
      </div>

      <!-- Transcript Section -->
      <div class="section transcript-section" v-if="appState.currentTranscript">
        <p class="transcript-text">{{ appState.currentTranscript }}</p>
      </div>

      <!-- Error Section -->
      <div class="section error-section" v-if="appState.errorMessage">
        <div class="error-content">
          <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{{ appState.errorMessage }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-panel {
  width: 320px;
  height: 100%;
  background: #1C1C1E;
  border-radius: 24px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

/* Action Bar */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px;
  margin: 12px 12px 0;
  background: rgba(18, 18, 18, 0.8);
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.action-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 12px;
  flex: 1;
  min-width: 0;
}

.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transition: background 0.3s ease;
  flex-shrink: 0;
}

.status-indicator.connected {
  background: #52c41a;
  box-shadow: 0 0 8px rgba(82, 196, 26, 0.5);
}

.status-text {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  white-space: nowrap;
}

.status-divider {
  color: rgba(255, 255, 255, 0.2);
}

.buffer-info {
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
  margin-left: auto;
  padding-right: 8px;
}

.mic-button {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #2979FF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 16px;
}

.mic-button:hover:not(:disabled) {
  background: #448AFF;
  transform: scale(1.05);
}

.mic-button:disabled {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.3);
  cursor: not-allowed;
}

.mic-button.active {
  background: #ff4d4f;
}

.mic-button.active:hover:not(:disabled) {
  background: #ff7875;
}

/* Panel Content */
.panel-content {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.section {
  margin-bottom: 16px;
}

/* Config Section */
.config-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(44, 44, 46, 0.5);
  border-radius: 16px;
  padding: 16px;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-icon {
  width: 18px;
  height: 18px;
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.config-label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  flex: 1;
}

.config-select {
  width: 110px;
}

/* Transcript Section */
.transcript-section {
  background: rgba(44, 44, 46, 0.5);
  border-radius: 16px;
  padding: 16px;
}

.transcript-text {
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  line-height: 1.6;
}

/* Error Section */
.error-section {
  background: rgba(255, 77, 79, 0.1);
  border-radius: 12px;
  padding: 12px 16px;
  border: 1px solid rgba(255, 77, 79, 0.3);
}

.error-content {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ff7875;
  font-size: 13px;
}

.error-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

/* Dark theme overrides for Ant Design */
:deep(.ant-select) {
  background: transparent;
}

:deep(.ant-select-selector) {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 8px !important;
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.ant-select-arrow) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.ant-select-selection-item) {
  color: rgba(255, 255, 255, 0.8) !important;
}

:deep(.ant-select-disabled .ant-select-selector) {
  background: rgba(255, 255, 255, 0.04) !important;
  color: rgba(255, 255, 255, 0.3) !important;
}

:deep(.ant-switch) {
  background: rgba(255, 255, 255, 0.15);
}

:deep(.ant-switch-checked) {
  background: #2979FF !important;
}
</style>
