export default {
  // Settings Panel
  settings: {
    title: 'Settings',
    asrLanguage: 'Recognition Language',
    correction: 'Text Correction',
    translate: 'Translation',
    uiLanguage: 'UI Language',
    tabs: {
      general: 'General',
      llm: 'LLM',
      asr: 'ASR',
    },
    // LLM Settings
    llm: {
      provider: 'Provider',
      apiKey: 'API Key',
      apiKeyPlaceholder: 'Leave empty for default',
      apiBase: 'API Base',
      model: 'Model',
      timeout: 'Timeout (s)',
      temperature: 'Temperature',
    },
    // ASR Settings
    asr: {
      modelPath: 'Model Path',
      browse: 'Browse',
      localModels: 'Local Models',
      availableModels: 'Available Models',
      download: 'Download',
      downloading: 'Downloading...',
      noLocalModels: 'No local models',
    },
    // Shortcut Settings
    shortcut: {
      title: 'Shortcuts',
      toggleRecording: 'Toggle Recording',
      save: 'Save',
      invalid: 'Invalid shortcut',
    },
  },

  // Floating Ball Actions
  actions: {
    record: 'Record',
    language: 'Language',
    translate: 'Translate',
    correction: 'Correction',
    settings: 'Settings',
  },

  // ASR Language Options
  asrLanguages: {
    auto: 'Auto Detect',
    zh: '中文',
    en: 'English',
    ja: '日本語',
    ko: '한국어',
    yue: 'Cantonese',
  },

  // Translation Target Languages
  translateLanguages: {
    none: 'Off',
    zh: '中文',
    en: 'English',
    ja: '日本語',
    ko: '한국어',
    fr: 'Français',
    de: 'Deutsch',
    es: 'Español',
  },

  // Locale Options
  locales: {
    zh: '中文',
    en: 'English',
  },
}
