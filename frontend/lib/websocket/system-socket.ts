import type { ConnectionState, SystemHeartbeat } from "@/lib/types/system";


const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/system";
const MAX_RETRY_DELAY_MS = 15_000;

interface SystemSocketCallbacks {
  onStateChange: (state: ConnectionState) => void;
  onHeartbeat: (heartbeat: SystemHeartbeat) => void;
}


export function connectSystemSocket(callbacks: SystemSocketCallbacks): () => void {
  let socket: WebSocket | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let retryCount = 0;
  let stopped = false;

  const connect = () => {
    if (stopped) return;
    callbacks.onStateChange("CONNECTING");
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      retryCount = 0;
      callbacks.onStateChange("CONNECTED");
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string) as SystemHeartbeat;
        if (message.type === "system.heartbeat") callbacks.onHeartbeat(message);
      } catch (error) {
        console.error("Invalid system WebSocket message", error);
      }
    };

    socket.onclose = () => {
      callbacks.onStateChange("DISCONNECTED");
      if (stopped) return;
      const delay = Math.min(1000 * 2 ** retryCount, MAX_RETRY_DELAY_MS);
      retryCount += 1;
      retryTimer = setTimeout(connect, delay);
    };

    socket.onerror = () => socket?.close();
  };

  connect();

  return () => {
    stopped = true;
    if (retryTimer) clearTimeout(retryTimer);
    socket?.close();
  };
}

