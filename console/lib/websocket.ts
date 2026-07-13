class ConsoleWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  connect() {
    const url = (process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000') + '/ws/live';
    this.ws = new WebSocket(url);
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.emit(data.type || 'message', data);
    };
    this.ws.onclose = () => setTimeout(() => this.connect(), 5000);
  }

  on(event: string, cb: (data: any) => void) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event)!.add(cb);
    return () => this.listeners.get(event)?.delete(cb);
  }

  private emit(event: string, data: any) {
    this.listeners.get(event)?.forEach(cb => cb(data));
  }
}

export const ws = new ConsoleWebSocket();
