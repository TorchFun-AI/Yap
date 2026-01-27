/**
 * Tauri Bridge Service
 * Handles communication between frontend and Tauri/backend
 */

import { invoke } from '@tauri-apps/api/core'

export interface BackendStatus {
  running: boolean
  port: number
}

export async function greet(name: string): Promise<string> {
  return await invoke('greet', { name })
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch('http://127.0.0.1:8765/health')
    const data = await response.json()
    return data.status === 'ok'
  } catch {
    return false
  }
}

export function createAudioWebSocket(): WebSocket {
  return new WebSocket('ws://127.0.0.1:8765/ws/audio')
}

export interface AudioDevice {
  id: number
  name: string
  channels: number
  default: boolean
}

export async function getAudioDevices(): Promise<AudioDevice[]> {
  try {
    const response = await fetch('http://127.0.0.1:8765/api/devices')
    const data = await response.json()
    return data.devices
  } catch {
    return []
  }
}
