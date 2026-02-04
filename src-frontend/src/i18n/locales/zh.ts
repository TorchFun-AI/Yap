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
}
