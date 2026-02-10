import { invoke } from '@tauri-apps/api/core'

const HTTP_BASE_KEY = 'vocistant-http-base'
const WS_BASE_KEY = 'vocistant-ws-base'
const DEFAULT_HTTP_BASE = 'http://127.0.0.1:8765'
const DEFAULT_WS_BASE = 'ws://127.0.0.1:8765'

export async function initPort(): Promise<void> {
  try {
    const port = await invoke<number>('get_backend_port')
    localStorage.setItem(HTTP_BASE_KEY, `http://127.0.0.1:${port}`)
    localStorage.setItem(WS_BASE_KEY, `ws://127.0.0.1:${port}`)
  } catch {
    // 保持 localStorage 中已有的值，或使用默认值
  }
}

export function httpUrl(path: string): string {
  const base = localStorage.getItem(HTTP_BASE_KEY) || DEFAULT_HTTP_BASE
  return `${base}${path}`
}

export function wsUrl(path: string): string {
  const base = localStorage.getItem(WS_BASE_KEY) || DEFAULT_WS_BASE
  return `${base}${path}`
}
