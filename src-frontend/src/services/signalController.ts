/**
 * Signal Controller Service
 * Sends control signals to backend via WebSocket (no audio capture)
 */

import {
  ConnectionStatus as ConnectionStatusConst,
  WS_MAX_RETRIES,
  WS_BASE_RETRY_DELAY,
  WS_MAX_RETRY_DELAY,
  WsMessageType,
  ControlAction,
} from '@/constants'

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
export type MessageHandler = (data: unknown) => void
export type ConnectionStatusHandler = (status: ConnectionStatus, retryCount?: number) => void

export class SignalController {
  private ws: WebSocket | null = null
  private messageHandler: MessageHandler | null = null
  private connectionStatusHandler: ConnectionStatusHandler | null = null
  private _connectionStatus: ConnectionStatus = ConnectionStatusConst.DISCONNECTED
  private wsUrl: string = ''
  private retryCount = 0
  private maxRetries = WS_MAX_RETRIES
  private baseRetryDelay = WS_BASE_RETRY_DELAY
  private maxRetryDelay = WS_MAX_RETRY_DELAY
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private manualDisconnect = false

  async connect(wsUrl: string): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) return

    this.wsUrl = wsUrl
    this.manualDisconnect = false
    this.retryCount = 0
    await this.doConnect()
  }

  private async doConnect(): Promise<void> {
    if (this.manualDisconnect) return

    const isReconnect = this.retryCount > 0
    this.setConnectionStatus(isReconnect ? ConnectionStatusConst.RECONNECTING : ConnectionStatusConst.CONNECTING)

    try {
      this.ws = new WebSocket(this.wsUrl)

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.messageHandler?.(data)
      }

      await new Promise<void>((resolve, reject) => {
        this.ws!.onopen = () => {
          this.retryCount = 0
          this.setConnectionStatus(ConnectionStatusConst.CONNECTED)
          resolve()
        }
        this.ws!.onerror = () => reject(new Error('WebSocket connection failed'))
      })

      this.ws.onclose = () => {
        if (!this.manualDisconnect) {
          this.setConnectionStatus(ConnectionStatusConst.DISCONNECTED)
          this.scheduleReconnect()
        }
      }
    } catch {
      this.setConnectionStatus(ConnectionStatusConst.DISCONNECTED)
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.manualDisconnect || this.retryCount >= this.maxRetries) {
      return
    }

    this.retryCount++
    const delay = Math.min(
      this.baseRetryDelay * Math.pow(2, this.retryCount - 1),
      this.maxRetryDelay
    )

    this.retryTimer = setTimeout(() => {
      this.doConnect()
    }, delay)
  }

  private setConnectionStatus(status: ConnectionStatus): void {
    this._connectionStatus = status
    this.connectionStatusHandler?.(status, this.retryCount)
  }

  startRecording(config: {
    language?: string
    correctionEnabled?: boolean
    targetLanguage?: string
    asrModelPath?: string
    // LLM 配置
    llmApiKey?: string
    llmApiBase?: string
    llmModel?: string
    llmTimeout?: number
    llmTemperature?: number
  } = {}): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({
      type: WsMessageType.CONTROL,
      action: ControlAction.START,
      config,
    }))
  }

  stopRecording(): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({
      type: WsMessageType.CONTROL,
      action: ControlAction.STOP,
    }))
  }

  updateConfig(config: {
    language?: string
    correctionEnabled?: boolean
    targetLanguage?: string
    asrModelPath?: string
  }): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({
      type: WsMessageType.CONTROL,
      action: 'update_config',
      config,
    }))
  }

  updateLlmConfig(config: {
    api_key?: string
    api_base?: string
    model?: string
    timeout?: number
    temperature?: number
  }): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({
      type: WsMessageType.CONTROL,
      action: 'update_llm_config',
      config,
    }))
  }

  disconnect(): void {
    this.manualDisconnect = true
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
    this.ws?.close()
    this.ws = null
    this.setConnectionStatus(ConnectionStatusConst.DISCONNECTED)
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandler = handler
  }

  onConnectionStatusChange(handler: ConnectionStatusHandler): void {
    this.connectionStatusHandler = handler
  }

  get connectionStatus(): ConnectionStatus {
    return this._connectionStatus
  }

  get isConnected(): boolean {
    return this._connectionStatus === ConnectionStatusConst.CONNECTED
  }
}

export const signalController = new SignalController()
