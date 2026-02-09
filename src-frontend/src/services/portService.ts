import { invoke } from '@tauri-apps/api/core'

let _port: number = 8765

export async function initPort(): Promise<void> {
  try {
    _port = await invoke<number>('get_backend_port')
  } catch {
    _port = 8765
  }
}

export function getPort(): number {
  return _port
}

export function httpUrl(path: string): string {
  return `http://127.0.0.1:${_port}${path}`
}

export function wsUrl(path: string): string {
  return `ws://127.0.0.1:${_port}${path}`
}
