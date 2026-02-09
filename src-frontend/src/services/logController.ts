/**
 * Log WebSocket Controller
 * Manages WebSocket connection for real-time log streaming from backend.
 */

import { wsUrl } from './portService'

export interface LogEntry {
  type: 'log'
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  logger: string
  message: string
}

type LogCallback = (entry: LogEntry) => void

class LogController {
  private ws: WebSocket | null = null
  private callbacks: Set<LogCallback> = new Set()
  private _isConnected = false

  get isConnected(): boolean {
    return this._isConnected
  }

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return
    }

    this.ws = new WebSocket(wsUrl('/ws/logs'))

    this.ws.onopen = () => {
      this._isConnected = true
      console.log('Log WebSocket connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const entry: LogEntry = JSON.parse(event.data)
        this.callbacks.forEach((cb) => cb(entry))
      } catch (e) {
        console.error('Failed to parse log entry:', e)
      }
    }

    this.ws.onclose = () => {
      this._isConnected = false
      console.log('Log WebSocket disconnected')
    }

    this.ws.onerror = (error) => {
      console.error('Log WebSocket error:', error)
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
      this._isConnected = false
    }
  }

  onLog(callback: LogCallback): () => void {
    this.callbacks.add(callback)
    return () => {
      this.callbacks.delete(callback)
    }
  }
}

export const logController = new LogController()
