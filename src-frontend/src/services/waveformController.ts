/**
 * 波形数据 WebSocket 控制器
 * 独立的 WebSocket 连接，用于接收实时声波数据
 */

export interface WaveformData {
  type: 'waveform'
  levels: number[]
}

class WaveformController {
  private ws: WebSocket | null = null
  private onDataCallback: ((levels: number[]) => void) | null = null
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private baseReconnectDelay = 1000
  private wsUrl: string = ''
  private isManualDisconnect = false

  /**
   * 连接到波形 WebSocket 端点
   */
  connect(wsUrl: string): void {
    this.wsUrl = wsUrl
    this.isManualDisconnect = false
    this.reconnectAttempts = 0
    this.createConnection()
  }

  private createConnection(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    try {
      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        console.log('[WaveformController] Connected to', this.wsUrl)
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WaveformData
          if (data.type === 'waveform' && Array.isArray(data.levels)) {
            // 确保数据是 7 个归一化值
            const levels = data.levels.slice(0, 7).map(v =>
              Math.max(0, Math.min(1, Number(v) || 0))
            )
            // 如果不足 7 个，补 0
            while (levels.length < 7) {
              levels.push(0)
            }
            this.onDataCallback?.(levels)
          }
        } catch (e) {
          // 忽略解析错误
        }
      }

      this.ws.onclose = () => {
        console.log('[WaveformController] Connection closed')
        if (!this.isManualDisconnect) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('[WaveformController] WebSocket error:', error)
      }
    } catch (e) {
      console.error('[WaveformController] Failed to create WebSocket:', e)
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.isManualDisconnect) return
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WaveformController] Max reconnect attempts reached')
      return
    }

    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      30000
    )
    this.reconnectAttempts++

    console.log(`[WaveformController] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimer = window.setTimeout(() => {
      this.createConnection()
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualDisconnect = true

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    console.log('[WaveformController] Disconnected')
  }

  /**
   * 注册数据回调
   */
  onData(callback: (levels: number[]) => void): void {
    this.onDataCallback = callback
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const waveformController = new WaveformController()
