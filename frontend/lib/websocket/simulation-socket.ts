import type { SimulationClockEvent, SimulationConnectionState } from "@/lib/types/simulation";


const WS_URL = process.env.NEXT_PUBLIC_SIMULATION_WS_URL ?? "ws://localhost:8000/ws/simulation";
const MAX_RETRY_DELAY_MS = 15_000;

interface SimulationSocketCallbacks {
  onStateChange: (state: SimulationConnectionState) => void;
  onClock: (event: SimulationClockEvent) => void;
}


export function connectSimulationSocket(callbacks: SimulationSocketCallbacks): () => void {
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

    socket.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data as string) as SimulationClockEvent;
        if (event.type === "simulation.clock") callbacks.onClock(event);
      } catch (error) {
        console.error("Invalid simulation WebSocket event", error);
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

