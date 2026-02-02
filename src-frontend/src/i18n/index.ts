import { createI18n } from 'vue-i18n'
import zh from './locales/zh'
import en from './locales/en'

// 系统语言检测
function getSystemLocale(): 'zh' | 'en' {
  // 优先从 localStorage 读取用户设置
  const savedLocale = localStorage.getItem('app-locale')
  if (savedLocale === 'zh' || savedLocale === 'en') {
    return savedLocale
  }

  // 检测系统语言
  const systemLang = navigator.language.toLowerCase()
  if (systemLang.startsWith('zh')) {
    return 'zh'
  }
  return 'en'
}

export const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  locale: getSystemLocale(),
  fallbackLocale: 'en',
  messages: {
    zh,
    en,
  },
})

// 切换语言并持久化
export function setLocale(locale: 'zh' | 'en') {
  i18n.global.locale.value = locale
  localStorage.setItem('app-locale', locale)
  document.documentElement.lang = locale
}

// 获取当前语言
export function getLocale(): 'zh' | 'en' {
  return i18n.global.locale.value as 'zh' | 'en'
}

export default i18n
