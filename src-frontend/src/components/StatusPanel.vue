<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { CloseOutlined, AudioOutlined, AudioMutedOutlined } from '@ant-design/icons-vue'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { useAppState } from '@/stores/appState'
import { signalController } from '@/services/signalController'
import {
  WS_DEFAULT_URL,
  RECORDING_DEFAULT_LANGUAGE,
  ConnectionStatus,
  AppStatus,
  WsMessageType,
  BackendStatus,
  StatusColorMap,
  ConnectionColorMap,
  StatusTextMap,
  ConnectionTextMap,
  TRANSLATE_LANGUAGES,
  ASR_LANGUAGES,
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
const asrLanguage = ref(RECORDING_DEFAULT_LANGUAGE)
const correctionEnabled = ref(true)
const targetLanguage = ref('')
let unlistenShortcut: UnlistenFn | null = null

const statusColor = computed(() => StatusColorMap[appState.status] || 'default')

const statusText = computed(() => StatusTextMap[appState.status] || appState.status)

const connectionColor = computed(() => ConnectionColorMap[appState.connectionStatus] || 'default')

const connectionText = computed(() => {
  if (appState.connectionStatus === ConnectionStatus.RECONNECTING) {
    return `Reconnecting (${appState.retryCount})...`
  }
  return ConnectionTextMap[appState.connectionStatus] || 'Disconnected'
})

onMounted(async () => {
  // 监听全局快捷键事件
  unlistenShortcut = await listen('toggle_recording', () => {
    if (appState.isConnected) {
      toggleRecording()
    }
  })

  signalController.onConnectionStatusChange((status, retry) => {
    const prevStatus = appState.connectionStatus
    appState.setConnectionStatus(status, retry)

    // 重连成功后重置状态，需要用户重新开始录音
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
      language: asrLanguage.value,
      correctionEnabled: correctionEnabled.value,
      targetLanguage: targetLanguage.value || undefined,
    })
    appState.setStatus(AppStatus.STARTING)
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
        <a-tag :color="connectionColor">
          {{ connectionText }}
        </a-tag>
      </div>

      <div class="config-row">
        <span class="label">ASR:</span>
        <a-select
          v-model:value="asrLanguage"
          :disabled="isRecording"
          :options="ASR_LANGUAGES"
          size="small"
          style="width: 120px"
        />
      </div>

      <div class="config-row">
        <span class="label">Correction:</span>
        <a-switch
          v-model:checked="correctionEnabled"
          :disabled="isRecording"
          size="small"
        />
      </div>

      <div class="config-row">
        <span class="label">Translate:</span>
        <a-select
          v-model:value="targetLanguage"
          :disabled="isRecording"
          :options="TRANSLATE_LANGUAGES"
          size="small"
          style="width: 120px"
          placeholder="不翻译"
        />
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
.config-row { display: flex; align-items: center; margin-bottom: 8px; }
.label { font-weight: 500; margin-right: 8px; color: #666; min-width: 80px; }
.record-control { display: flex; align-items: center; gap: 12px; margin: 16px 0; }
.record-hint { color: #666; font-size: 14px; }
.buffer-info { margin-left: 8px; color: #999; font-size: 12px; }
.transcript-area { margin-top: 16px; padding-top: 16px; border-top: 1px solid #f0f0f0; }
.transcript-area p { margin: 8px 0 0; color: #333; }
.error-area { margin-top: 16px; }
</style>
