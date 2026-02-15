export default {
  // 设置面板
  settings: {
    title: '设置',
    asrLanguage: '识别语言',
    correction: '文本校正',
    contextCorrection: '上下文校正',
    contextCount: '上下文数量',
    contextCountTip: '校正时参考的历史消息数量',
    translate: '翻译',
    translateLanguage: '翻译语言',
    maxHistory: '历史记录数量',
    uiLanguage: '界面语言',
    tabs: {
      general: '通用',
      voice: '输入处理',
      llm: 'LLM',
      asr: 'ASR',
      debug: '调试',
    },
    // LLM 设置
    llm: {
      provider: '服务商',
      apiKey: 'API 密钥',
      apiKeyPlaceholder: '留空使用默认',
      apiBase: 'API 地址',
      model: '模型',
      timeout: '超时(秒)',
      temperature: '温度',
    },
    // ASR 设置
    asr: {
      modelPath: '模型目录',
      browse: '浏览',
      localModels: '本地模型',
      availableModels: '可下载模型',
      download: '下载',
      downloading: '下载中...',
      noLocalModels: '暂无本地模型',
      useMirror: 'HuggingFace 镜像',
      useMirrorHint: '国内用户建议开启',
      delete: '删除',
      verify: '校验',
      deleteConfirm: '确认删除此模型？',
      verifying: '校验中...',
      verifySuccess: '模型完整',
      verifyFailed: '模型不完整',
      deleteSuccess: '删除成功',
      deleteFailed: '删除失败',
      models: {
        'mlx-community/Fun-ASR-MLT-Nano-2512-4bit': {
          description: '多语言语音识别模型 (4-bit 量化)',
        },
        'mlx-community/Fun-ASR-MLT-Nano-2512-8bit': {
          description: '多语言语音识别模型 (8-bit 量化)',
        },
        'mlx-community/whisper-large-v3-mlx': {
          description: 'OpenAI Whisper 大模型 MLX 版',
        },
      },
    },
    // 快捷键设置
    shortcut: {
      title: '快捷键',
      toggleRecording: '开始/停止录音',
      openSettings: '打开设置',
      save: '保存',
      invalid: '无效的快捷键',
    },
    // 输出方式设置
    autoInputMode: {
      label: '输出方式',
      input: '自动输入',
      clipboard: '复制到剪贴板',
      none: '仅识别',
    },
    // 调试设置
    debug: {
      connect: '连接',
      disconnect: '断开',
      clear: '清空',
      autoScroll: '自动滚动',
      filterLevel: '日志级别',
      connected: '已连接',
      disconnected: '未连接',
      noLogs: '暂无日志',
      copied: '已复制到剪贴板',
      devtools: '开发者工具',
    },
  },

  // 悬浮球操作项
  actions: {
    record: '录音',
    language: '识别语言',
    translate: '翻译',
    correction: '文本校正',
    settings: '设置',
  },

  // ASR 语言选项
  asrLanguages: {
    auto: '自动检测',
    zh: '中文',
    en: 'English',
    ja: '日本語',
    ko: '한국어',
    yue: '粤语',
  },

  // 翻译目标语言
  translateLanguages: {
    none: '不翻译',
    zh: '中文',
    en: 'English',
    ja: '日本語',
    ko: '한국어',
    fr: 'Français',
    de: 'Deutsch',
    es: 'Español',
  },

  // 界面语言选项
  locales: {
    zh: '中文',
    en: 'English',
  },

  // 系统消息
  systemMessages: {
    loadingModel: '正在加载模型…',
    downloadingModel: '正在下载模型…',
    recordingStarted: '录音已开始，请说话',
    recordingStopped: '录音已停止',
    idleTimeout: '录音超时，已自动停止',
    error: '发生错误',
  },
}
