import type { SystemStatus } from "@/lib/types/system";


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


export async function fetchSystemStatus(signal?: AbortSignal): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/system/status`, {
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(`System status request failed with HTTP ${response.status}`);
  }

  return (await response.json()) as SystemStatus;
}

