import type { SimulationAction, SimulationSnapshot } from "@/lib/types/simulation";


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


export class SimulationApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "SimulationApiError";
  }
}


async function parseResponse(response: Response): Promise<SimulationSnapshot> {
  if (!response.ok) {
    let message = `Simulation request failed with HTTP ${response.status}`;
    try {
      const body = await response.json() as { detail?: { message?: string } | string };
      message = typeof body.detail === "string" ? body.detail : body.detail?.message ?? message;
    } catch {
      // Preserve the HTTP fallback when a proxy or server returns a non-JSON error.
    }
    throw new SimulationApiError(message, response.status);
  }
  return await response.json() as SimulationSnapshot;
}


export async function fetchSimulation(signal?: AbortSignal): Promise<SimulationSnapshot> {
  return parseResponse(await fetch(`${API_BASE_URL}/api/v1/simulation`, {
    cache: "no-store",
    signal,
  }));
}


export async function performSimulationAction(action: SimulationAction): Promise<SimulationSnapshot> {
  return parseResponse(await fetch(`${API_BASE_URL}/api/v1/simulation/${action}`, {
    method: "POST",
  }));
}


export async function updateSimulationSpeed(speedMultiplier: number): Promise<SimulationSnapshot> {
  return parseResponse(await fetch(`${API_BASE_URL}/api/v1/simulation/speed`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed_multiplier: speedMultiplier }),
  }));
}


export async function stepSimulation(seconds: number): Promise<SimulationSnapshot> {
  return parseResponse(await fetch(`${API_BASE_URL}/api/v1/simulation/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seconds }),
  }));
}

