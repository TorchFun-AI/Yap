<script setup lang="ts">
import { computed } from 'vue'
import { useAppState } from '@/stores/appState'
import { ASR_LANGUAGES, TRANSLATE_LANGUAGES, AppStatus } from '@/constants'

const emit = defineEmits<{
  close: []
}>()

const appState = useAppState()

// 录音中时禁用配置修改
const isRecording = computed(() =>
  appState.status === AppStatus.STARTING ||
  appState.status === AppStatus.LISTENING ||
  appState.status === AppStatus.TRANSCRIBING ||
  appState.status === AppStatus.CORRECTING ||
  appState.status === AppStatus.TRANSLATING ||
  appState.status === AppStatus.SPEAKING
)
</script>

<template>
  <div class="settings-panel">
    <!-- 面板头部 -->
    <div class="panel-header">
      <span class="panel-title">设置</span>
      <button class="close-btn" @click="emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- 配置内容 -->
    <div class="panel-content">
      <!-- Language -->
      <div class="config-item">
        <svg class="config-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
        <span class="config-label">识别语言</span>
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

      <!-- Correction -->
      <div class="config-item">
        <svg class="config-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
        </svg>
        <span class="config-label">文本校正</span>
        <a-switch
          :checked="appState.correctionEnabled"
          @update:checked="appState.setCorrectionEnabled"
          :disabled="isRecording"
          size="small"
        />
      </div>

      <!-- Translate -->
      <div class="config-item">
        <svg class="config-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M5 8l6 6" />
          <path d="M4 14l6-6 2-3" />
          <path d="M2 5h12" />
          <path d="M7 2h1" />
          <path d="M22 22l-5-10-5 10" />
          <path d="M14 18h6" />
        </svg>
        <span class="config-label">翻译</span>
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
  </div>
</template>

<style scoped>
.settings-panel {
  background: rgba(45, 45, 48, 0.85);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
  padding: 12px;
  position: absolute;
  top: calc(100% + 8px);
  /* 与操作面板对齐：悬浮球宽度56px - 操作面板margin-left 20px = 36px */
  left: 36px;
  z-index: 100;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.panel-title {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 500;
}

.close-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
}

.close-btn svg {
  width: 14px;
  height: 14px;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.config-icon {
  width: 16px;
  height: 16px;
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.config-label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  flex: 1;
}

.config-select {
  width: 90px;
}

/* Ant Design 深色主题覆盖 */
:deep(.ant-select-selector) {
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 6px !important;
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 12px !important;
}

:deep(.ant-select-arrow) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.ant-select-selection-item) {
  color: rgba(255, 255, 255, 0.8) !important;
  font-size: 12px !important;
}

:deep(.ant-select-disabled .ant-select-selector) {
  background: rgba(255, 255, 255, 0.04) !important;
  color: rgba(255, 255, 255, 0.3) !important;
}

:deep(.ant-switch) {
  background: rgba(255, 255, 255, 0.15);
  min-width: 36px;
}

:deep(.ant-switch-checked) {
  background: #4A90E2 !important;
}
</style>
