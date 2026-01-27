/**
 * Signal Controller Service
 * Sends control signals to backend via WebSocket (no audio capture)
 */

export type MessageHandler = (data: unknown) => void

export class SignalController {
  private ws: WebSocket | null = null
  private messageHandler: MessageHandler | null = null
  private _isConnected = false

  async connect(wsUrl: string): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) return

    this.ws = new WebSocket(wsUrl)

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      this.messageHandler?.(data)
    }

    await new Promise<void>((resolve, reject) => {
      this.ws!.onopen = () => {
        this._isConnected = true
        resolve()
      }
      this.ws!.onerror = () => reject(new Error('WebSocket connection failed'))
    })

    this.ws.onclose = () => {
      this._isConnected = false
    }
  }

  startRecording(config: { language?: string } = {}): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({
      type: 'control',
      action: 'start',
      config,
    }))
  }

  stopRecording(): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({
      type: 'control',
      action: 'stop',
    }))
  }

  disconnect(): void {
    this.ws?.close()
    this.ws = null
    this._isConnected = false
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandler = handler
  }

  get isConnected(): boolean {
    return this._isConnected
  }
}

export const signalController = new SignalController()
