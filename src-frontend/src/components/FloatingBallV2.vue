<script setup lang="ts">
import { ref, computed } from 'vue'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { useAppState } from '@/stores/appState'
import { BallIconColorMap, AppStatus } from '@/constants'

interface ActionItem {
  id: string
  icon: string
  label: string
  options?: { value: string; label: string }[]
  toggle?: boolean // 是否为开关型按钮
}

const props = defineProps<{
  actions?: ActionItem[]
  settingsOpen?: boolean
}>()

const emit = defineEmits<{
  click: []
  action: [id: string, value?: string]
  drag: []
}>()

const appState = useAppState()
const isExpanded = ref(false)
const activeDropdown = ref<string | null>(null)
const hoveredAction = ref<string | null>(null)

const iconColor = computed(() => BallIconColorMap[appState.status] || BallIconColorMap[AppStatus.IDLE])
const isActive = computed(() => appState.isActive)

// 录音按钮是否禁用（仅在初始化中或未连接时禁用，说话/转写等状态可以停止）
const isRecordDisabled = computed(() =>
  appState.status === AppStatus.STARTING || !appState.isConnected
)

// 当前选中的值（从全局状态获取）
const selectedValues = computed(() => ({
  language: appState.asrLanguage,
  translate: appState.targetLanguage,
  correction: appState.correctionEnabled,
}))

// 默认操作项
const defaultActions: ActionItem[] = [
  {
    id: 'record',
    icon: 'mic',
    label: '录音',
  },
  {
    id: 'language',
    icon: 'globe',
    label: '识别语言',
    options: [
      { value: 'auto', label: '自动检测' },
      { value: 'zh', label: '中文' },
      { value: 'en', label: 'English' },
      { value: 'ja', label: '日本語' },
    ]
  },
  {
    id: 'translate',
    icon: 'translate',
    label: '翻译',
    options: [
      { value: '', label: '不翻译' },
      { value: '中文', label: '中文' },
      { value: 'English', label: 'English' },
      { value: '日本語', label: '日本語' },
    ]
  },
  {
    id: 'correction',
    icon: 'edit',
    label: '文本校正',
  },
  {
    id: 'settings',
    icon: 'settings',
    label: '设置',
  },
]

const actionItems = computed(() => props.actions || defaultActions)

const onMouseEnter = () => {
  // 不再通过 hover 展开
}

const onMouseLeave = () => {
  // 离开时不收起，只有点击悬浮球或拖动时才收起
}

// 拖动相关
let isDragging = false
let dragStartTime = 0

const onBallMouseDown = () => {
  isDragging = false
  dragStartTime = Date.now()
}

const onBallMouseMove = async (e: MouseEvent) => {
  // 如果按住鼠标移动超过 100ms，认为是拖动
  if (e.buttons === 1 && Date.now() - dragStartTime > 100) {
    isDragging = true
    // 进入拖动状态时收起操作区
    if (isExpanded.value) {
      isExpanded.value = false
      activeDropdown.value = null
      hoveredAction.value = null
    }
    // 通知父组件关闭设置面板
    emit('drag')
    const appWindow = getCurrentWindow()
    await appWindow.startDragging()
  }
}

const onBallClick = () => {
  // 如果是拖动操作，不触发点击
  if (isDragging) {
    isDragging = false
    return
  }
  // 点击悬浮球展开/收起操作区
  isExpanded.value = !isExpanded.value
  if (!isExpanded.value) {
    activeDropdown.value = null
    hoveredAction.value = null
  }
}

const onActionClick = (action: ActionItem) => {
  // 设置面板打开时，只允许点击设置按钮
  if (props.settingsOpen && action.id !== 'settings') return

  if (action.options) {
    activeDropdown.value = activeDropdown.value === action.id ? null : action.id
  } else if (action.id === 'record') {
    // 录音开关，检查是否禁用
    if (isRecordDisabled.value) return
    emit('action', 'record', isActive.value ? 'stop' : 'start')
  } else if (action.id === 'correction') {
    // 文本校正开关
    appState.setCorrectionEnabled(!appState.correctionEnabled)
    emit('action', action.id, appState.correctionEnabled ? 'on' : 'off')
  } else if (action.id === 'settings') {
    // 设置面板
    emit('action', 'settings')
  }
}

const onOptionSelect = (actionId: string, value: string) => {
  // 更新全局状态
  if (actionId === 'language') {
    appState.setAsrLanguage(value)
  } else if (actionId === 'translate') {
    appState.setTargetLanguage(value)
  }
  emit('action', actionId, value)
  activeDropdown.value = null
}

const onActionHover = (actionId: string | null) => {
  hoveredAction.value = actionId
}

// 暴露展开状态给父组件
defineExpose({
  isExpanded,
  hasDropdown: computed(() => activeDropdown.value !== null),
})

// 图标 SVG 路径
const iconPaths: Record<string, string> = {
  globe: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z',
  translate: 'M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z',
  edit: 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z',
  mic: 'M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z',
  sparkles: 'M12 3L13.5 8.5L19 10L13.5 11.5L12 17L10.5 11.5L5 10L10.5 8.5L12 3ZM19 16L20 18.5L22.5 19.5L20 20.5L19 23L18 20.5L15.5 19.5L18 18.5L19 16Z',
  settings: 'M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z',
}
</script>

<template>
  <div
    class="floating-ball-container"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <!-- 主按钮 -->
    <div
      class="main-button"
      :class="{ expanded: isExpanded }"
      @click="onBallClick"
      @mousedown="onBallMouseDown"
      @mousemove="onBallMouseMove"
    >
      <!-- Idle: Sparkles 图标 -->
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

      <!-- 呼吸灯效果 -->
      <div v-if="!isExpanded && isActive" class="pulse-ring" :style="{ background: iconColor }" />
    </div>

    <!-- 展开的操作面板（从左侧展开） -->
    <transition name="panel-expand">
      <div v-show="isExpanded" class="action-panel">
        <div
          v-for="(action, index) in actionItems"
          :key="action.id"
          class="action-item"
          :style="{ transitionDelay: `${index * 50}ms` }"
          @click="onActionClick(action)"
          @mouseenter="onActionHover(action.id)"
          @mouseleave="onActionHover(null)"
        >
          <div class="action-icon" :class="{
            active: activeDropdown === action.id,
            toggled: (action.id === 'correction' && selectedValues.correction) || (action.id === 'record' && isActive) || (action.id === 'settings' && props.settingsOpen),
            disabled: (action.id === 'record' && isRecordDisabled) || (action.id !== 'settings' && props.settingsOpen)
          }">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path :d="iconPaths[action.icon] || iconPaths.sparkles" />
            </svg>
          </div>

          <!-- Tooltip -->
          <transition name="tooltip-fade">
            <div
              v-if="hoveredAction === action.id && activeDropdown !== action.id"
              class="tooltip"
            >
              {{ action.label }}
            </div>
          </transition>

          <!-- Dropdown Menu -->
          <transition name="dropdown-slide">
            <div v-if="activeDropdown === action.id && action.options" class="dropdown-menu">
              <div
                v-for="option in action.options"
                :key="option.value"
                class="dropdown-item"
                :class="{ selected: selectedValues[action.id as keyof typeof selectedValues] === option.value }"
                @click.stop="onOptionSelect(action.id, option.value)"
              >
                {{ option.label }}
              </div>
            </div>
          </transition>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.floating-ball-container {
  display: flex;
  align-items: center;
  position: relative;
}

/* 主按钮 */
.main-button {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 10;
  background: linear-gradient(180deg, #2C2C2E 0%, #1C1C1E 100%);
  border: 2px solid #4A90E2;
  box-shadow: 0 0 12px rgba(74, 144, 226, 0.5);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  flex-shrink: 0;
}

.main-button:hover {
  transform: scale(1.05);
  box-shadow: 0 0 20px rgba(74, 144, 226, 0.6);
}

.main-button:active {
  transform: scale(0.95);
}

.main-button.expanded {
  border-color: rgba(74, 144, 226, 0.6);
}

.ball-icon {
  width: 24px;
  height: 24px;
  transition: color 0.3s ease;
}

/* 呼吸灯效果 */
.pulse-ring {
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

/* 操作面板 - 从右侧展开，尺寸更小 */
.action-panel {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 12px;
  margin-left: -20px;
  padding-left: 28px;
  background: rgba(45, 45, 48, 0.85);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
  gap: 8px;
}

/* 操作项 */
.action-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  color: rgba(255, 255, 255, 0.7);
}

.action-icon:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.action-icon:active {
  transform: scale(0.95);
}

.action-icon.active {
  background: rgba(74, 144, 226, 0.2);
  color: #4A90E2;
}

.action-icon.toggled {
  background: rgba(74, 144, 226, 0.3);
  color: #4A90E2;
  box-shadow: 0 0 8px rgba(74, 144, 226, 0.4);
}

.action-icon.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-icon.disabled:hover {
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
}

.action-icon svg {
  width: 18px;
  height: 18px;
}

/* Tooltip */
.tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: 5px 8px;
  background: rgba(30, 30, 30, 0.95);
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #ffffff;
  white-space: nowrap;
  pointer-events: none;
  z-index: 100;
}

.tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: rgba(30, 30, 30, 0.95);
}

/* Dropdown Menu */
.dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 100px;
  padding: 4px 0;
  background: rgba(30, 30, 30, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.dropdown-item {
  padding: 6px 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.15s ease;
}

.dropdown-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.dropdown-item.selected {
  background: rgba(74, 144, 226, 0.2);
  color: #4A90E2;
}

.dropdown-item.selected::before {
  content: '✓';
  margin-right: 6px;
  font-size: 10px;
}

/* 面板展开动画 - 从左侧展开 */
.panel-expand-enter-active {
  animation: panelExpandIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.panel-expand-leave-active {
  animation: panelExpandOut 0.2s ease-out;
}

@keyframes panelExpandIn {
  0% {
    opacity: 0;
    transform: scaleX(0);
    transform-origin: left center;
  }
  100% {
    opacity: 1;
    transform: scaleX(1);
    transform-origin: left center;
  }
}

@keyframes panelExpandOut {
  0% {
    opacity: 1;
    transform: scaleX(1);
    transform-origin: left center;
  }
  100% {
    opacity: 0;
    transform: scaleX(0);
    transform-origin: left center;
  }
}

/* Tooltip 动画 */
.tooltip-fade-enter-active,
.tooltip-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.tooltip-fade-enter-from,
.tooltip-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(4px);
}

/* Dropdown 动画 */
.dropdown-slide-enter-active {
  animation: dropdownSlideIn 0.2s ease-out;
}

.dropdown-slide-leave-active {
  animation: dropdownSlideOut 0.15s ease-in;
}

@keyframes dropdownSlideIn {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(-8px);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes dropdownSlideOut {
  0% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateX(-50%) translateY(-8px);
  }
}
</style>
