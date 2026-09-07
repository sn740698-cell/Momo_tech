type MessageHandler = (data: any) => void;

class MomoWebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectTimer: any = null;
  private pingInterval: any = null;
  private listeners: Map<string, Set<MessageHandler>> = new Map();
  public isConnected: boolean = false;

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.port === '5173' ? '127.0.0.1:8000' : window.location.host;
    this.url = `${protocol}//${host}/ws/momo/`;
  }

  public connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.emit('connection', { online: true });
        this.startPing();
        console.log('[MOMO-WS] Connected to /ws/momo/');
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const type = payload.type || 'message';
          this.emit(type, payload);
          this.emit('*', payload);
        } catch (e) {
          console.error('[MOMO-WS] Failed to parse JSON message', e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.emit('connection', { online: false });
        this.stopPing();
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn('[MOMO-WS] WebSocket error:', err);
      };
    } catch (err) {
      console.error('[MOMO-WS] Connection error:', err);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      console.log('[MOMO-WS] Attempting reconnect...');
      this.connect();
    }, 3000);
  }

  private startPing() {
    this.stopPing();
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 15000);
  }

  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  public send(payload: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
      return true;
    }
    console.warn('[MOMO-WS] Cannot send, socket not open');
    return false;
  }

  public sendChatMessage(message: string, sessionId: string = 'default', model?: string) {
    return this.send({
      type: 'chat_message',
      message,
      session_id: sessionId,
      model,
      timestamp: Date.now(),
    });
  }

  public sendDeviceCommand(expression: string, animation: string = 'none', led?: string) {
    return this.send({
      type: 'device_command',
      expression,
      animation,
      led,
      timestamp: Date.now(),
    });
  }

  public on(event: string, handler: MessageHandler) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);
    return () => this.off(event, handler);
  }

  public off(event: string, handler: MessageHandler) {
    const set = this.listeners.get(event);
    if (set) {
      set.delete(handler);
    }
  }

  private emit(event: string, data: any) {
    const set = this.listeners.get(event);
    if (set) {
      set.forEach((fn) => {
        try {
          fn(data);
        } catch (e) {
          console.error(`[MOMO-WS] Listener error on '${event}'`, e);
        }
      });
    }
  }
}

export const momoSocket = new MomoWebSocketClient();
