export default {
  // 设置面板
  settings: {
    title: '设置',
    asrLanguage: '识别语言',
    correction: '文本校正',
    translate: '翻译',
    uiLanguage: '界面语言',
    tabs: {
      general: '通用',
      llm: 'LLM',
      asr: 'ASR',
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
