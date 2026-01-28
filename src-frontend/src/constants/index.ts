// WebSocket 默认配置
export const WS_DEFAULT_URL = 'ws://127.0.0.1:8765/ws/audio'

// WebSocket 重连配置
export const WS_MAX_RETRIES = 10
export const WS_BASE_RETRY_DELAY = 1000
export const WS_MAX_RETRY_DELAY = 30000

// 录音默认配置
export const RECORDING_DEFAULT_LANGUAGE = 'zh'

// 窗口配置
export const WINDOW_PANEL_WIDTH = 320
export const WINDOW_PANEL_HEIGHT = 220
export const WINDOW_BALL_SIZE = 60
export const WINDOW_GAP = 8
export const WINDOW_SHADOW = 16

// 默认窗口位置
export const DEFAULT_WINDOW_POSITION = { x: 100, y: 100 }

// 控制命令
export const ControlAction = {
  START: 'start',
  STOP: 'stop',
} as const

// 连接状态
export const ConnectionStatus = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
} as const

// 应用状态
export const AppStatus = {
  IDLE: 'idle',
  LISTENING: 'listening',
  TRANSCRIBING: 'transcribing',
  CORRECTING: 'correcting',
  SPEAKING: 'speaking',
  ERROR: 'error',
} as const

// WebSocket 消息类型
export const WsMessageType = {
  TRANSCRIPTION: 'transcription',
  CORRECTION: 'correction',
  VAD: 'vad',
  STATUS: 'status',
  ERROR: 'error',
  CONTROL: 'control',
} as const

// 后端状态映射
export const BackendStatus = {
  RECORDING: 'recording',
  STOPPED: 'stopped',
  TRANSCRIBING: 'transcribing',
  CORRECTING: 'correcting',
  SPEAKING: 'speaking',
} as const

// UI 颜色映射
export const StatusColorMap: Record<string, string> = {
  [AppStatus.SPEAKING]: 'orange',
  [AppStatus.TRANSCRIBING]: 'blue',
  [AppStatus.CORRECTING]: 'purple',
  [AppStatus.LISTENING]: 'green',
  [AppStatus.ERROR]: 'red',
  [AppStatus.IDLE]: 'default',
}

export const ConnectionColorMap: Record<string, string> = {
  [ConnectionStatus.CONNECTED]: 'success',
  [ConnectionStatus.CONNECTING]: 'processing',
  [ConnectionStatus.RECONNECTING]: 'warning',
  [ConnectionStatus.DISCONNECTED]: 'default',
}

// UI 文本映射
export const StatusTextMap: Record<string, string> = {
  [AppStatus.SPEAKING]: 'Speaking',
  [AppStatus.TRANSCRIBING]: 'Transcribing',
  [AppStatus.CORRECTING]: 'Correcting',
  [AppStatus.LISTENING]: 'Listening',
  [AppStatus.IDLE]: 'Idle',
  [AppStatus.ERROR]: 'Error',
}

export const ConnectionTextMap: Record<string, string> = {
  [ConnectionStatus.CONNECTED]: 'Connected',
  [ConnectionStatus.CONNECTING]: 'Connecting...',
  [ConnectionStatus.DISCONNECTED]: 'Disconnected',
}
