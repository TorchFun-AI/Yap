/**
 * Tauri Bridge Service
 * Handles communication between frontend and Tauri/backend
 */

import { invoke } from '@tauri-apps/api/core'
import { httpUrl, wsUrl } from './portService'

export interface BackendStatus {
  running: boolean
  port: number
}

export async function greet(name: string): Promise<string> {
  return await invoke('greet', { name })
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(httpUrl('/health'))
    const data = await response.json()
    return data.status === 'ok'
  } catch {
    return false
  }
}

export function createAudioWebSocket(): WebSocket {
  return new WebSocket(wsUrl('/ws/audio'))
}

export interface AudioDevice {
  id: number
  name: string
  channels: number
  default: boolean
}

export async function getAudioDevices(): Promise<AudioDevice[]> {
  try {
    const response = await fetch(httpUrl('/api/devices'))
    const data = await response.json()
    return data.devices
  } catch {
    return []
  }
}
