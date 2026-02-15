// WebSocket 路径（host:port 由 portService 提供）
export const WS_AUDIO_PATH = '/ws/audio'
export const WS_WAVEFORM_PATH = '/ws/waveform'

// WebSocket 重连配置
export const WS_MAX_RETRIES = Infinity
export const WS_BASE_RETRY_DELAY = 1000
export const WS_MAX_RETRY_DELAY = 30000

// 录音默认配置
export const RECORDING_DEFAULT_LANGUAGE = 'auto'

// 窗口配置
export const WINDOW_PANEL_WIDTH = 320
export const WINDOW_PANEL_HEIGHT = 280
export const WINDOW_BALL_SIZE = 56
export const WINDOW_GAP = 8
export const WINDOW_SHADOW = 32

// 设计系统颜色
export const DesignColors = {
  // 主色调
  SURFACE: '#121212',        // OLED 黑
  SURFACE_ALT: '#1C1C1E',    // 深灰
  PANEL_BG: 'rgba(44, 44, 46, 0.8)',
  BALL_BG: 'rgba(31, 31, 31, 0.9)',  // #1F1F1F 90%
  BALL_BORDER: 'rgba(255, 255, 255, 0.1)', // 亮色描边

  // 提亮色
  ACCENT: '#B388FF',         // Neon Purple
  ACCENT_ALT: '#9C27B0',     // Deep Purple

  // 文字颜色
  TEXT_PRIMARY: '#FFFFFF',
  TEXT_SECONDARY: 'rgba(255, 255, 255, 0.7)',
  TEXT_TERTIARY: 'rgba(255, 255, 255, 0.5)',
} as const

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
  STARTING: 'starting',
  LISTENING: 'listening',
  TRANSCRIBING: 'transcribing',
  CORRECTING: 'correcting',
  TRANSLATING: 'translating',
  SPEAKING: 'speaking',
  ERROR: 'error',
} as const

// WebSocket 消息类型
export const WsMessageType = {
  TRANSCRIPTION: 'transcription',
  TRANSCRIPTION_PARTIAL: 'transcription_partial',
  CORRECTION: 'correction',
  VAD: 'vad',
  STATUS: 'status',
  ERROR: 'error',
  CONTROL: 'control',
  TEXT_INPUT_REQUEST: 'text_input_request',
  CLIPBOARD_REQUEST: 'clipboard_request',
} as const

// 后端状态映射
export const BackendStatus = {
  STARTING: 'starting',
  DOWNLOADING: 'downloading',
  RECORDING: 'recording',
  STOPPED: 'stopped',
  TRANSCRIBING: 'transcribing',
  CORRECTING: 'correcting',
  TRANSLATING: 'translating',
  SPEAKING: 'speaking',
} as const

// UI 颜色映射 (Ant Design Tag 颜色名)
export const StatusColorMap: Record<string, string> = {
  [AppStatus.STARTING]: 'processing',
  [AppStatus.SPEAKING]: 'orange',
  [AppStatus.TRANSCRIBING]: 'blue',
  [AppStatus.CORRECTING]: 'purple',
  [AppStatus.TRANSLATING]: 'cyan',
  [AppStatus.LISTENING]: 'green',
  [AppStatus.ERROR]: 'red',
  [AppStatus.IDLE]: 'default',
}

// 悬浮球图标颜色映射 (用于图标颜色而非背景色)
export const BallIconColorMap: Record<string, string> = {
  [AppStatus.STARTING]: '#B388FF',    // Neon Purple
  [AppStatus.SPEAKING]: '#fa8c16',    // orange
  [AppStatus.TRANSCRIBING]: '#B388FF', // Neon Purple
  [AppStatus.CORRECTING]: '#B388FF',   // Neon Purple
  [AppStatus.TRANSLATING]: '#13c2c2',  // cyan
  [AppStatus.LISTENING]: '#52c41a',    // green
  [AppStatus.ERROR]: '#ff4d4f',        // red
  [AppStatus.IDLE]: '#FFFFFF',         // white
}

// 悬浮球颜色映射 (HEX 颜色值) - 保留用于兼容
export const BallColorMap: Record<string, string> = {
  [AppStatus.STARTING]: '#9C27B0',    // purple (processing)
  [AppStatus.SPEAKING]: '#fa8c16',    // orange
  [AppStatus.TRANSCRIBING]: '#9C27B0', // purple
  [AppStatus.CORRECTING]: '#722ed1',   // purple
  [AppStatus.TRANSLATING]: '#13c2c2',  // cyan
  [AppStatus.LISTENING]: '#52c41a',    // green
  [AppStatus.ERROR]: '#ff4d4f',        // red
  [AppStatus.IDLE]: '#8c8c8c',         // gray
}

export const ConnectionColorMap: Record<string, string> = {
  [ConnectionStatus.CONNECTED]: 'success',
  [ConnectionStatus.CONNECTING]: 'processing',
  [ConnectionStatus.RECONNECTING]: 'warning',
  [ConnectionStatus.DISCONNECTED]: 'default',
}

// UI 文本映射
export const StatusTextMap: Record<string, string> = {
  [AppStatus.STARTING]: 'Starting',
  [AppStatus.SPEAKING]: 'Speaking',
  [AppStatus.TRANSCRIBING]: 'Transcribing',
  [AppStatus.CORRECTING]: 'Correcting',
  [AppStatus.TRANSLATING]: 'Translating',
  [AppStatus.LISTENING]: 'Listening',
  [AppStatus.IDLE]: 'Idle',
  [AppStatus.ERROR]: 'Error',
}

export const ConnectionTextMap: Record<string, string> = {
  [ConnectionStatus.CONNECTED]: 'Connected',
  [ConnectionStatus.CONNECTING]: 'Connecting...',
  [ConnectionStatus.DISCONNECTED]: 'Disconnected',
}

// 翻译目标语言预设列表
export const TRANSLATE_LANGUAGES = [
  { value: '', label: '不翻译' },
  { value: '中文', label: '中文' },
  { value: 'English', label: 'English' },
  { value: '日本語', label: '日本語' },
  { value: '한국어', label: '한국어' },
  { value: 'Français', label: 'Français' },
  { value: 'Deutsch', label: 'Deutsch' },
  { value: 'Español', label: 'Español' },
] as const

// ASR 识别语言预设列表 (FunASR 支持的语言)
export const ASR_LANGUAGES = [
  { value: 'auto', label: '自动检测' },
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'yue', label: '粤语' },
] as const
