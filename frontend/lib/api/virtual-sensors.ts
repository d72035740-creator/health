import type { VirtualSensorConfiguration, WearableSensorWindow } from "@/lib/types/virtual-sensors";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export type SensorWindowRequest = { motion_condition: "STABLE_REST" | "ACTIVE_MOTION" | "POSTURE_TRANSITION"; contact_condition: "NOMINAL_CONTACT" | "UNSTABLE_CONTACT" | "POOR_CONTACT"; temperature_offset_c: number; };

async function parse<T>(response: Response): Promise<T> { if (!response.ok) { const body = await response.json().catch(() => null) as { detail?: { message?: string } | string } | null; throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.message ?? `Virtual sensor request failed with HTTP ${response.status}`); } return response.json() as Promise<T>; }
export async function fetchVirtualSensorConfig(signal?: AbortSignal): Promise<VirtualSensorConfiguration> { return parse(await fetch(`${API_BASE_URL}/api/v1/virtual-sensors/config`, { cache: "no-store", signal })); }
export async function acquireSensorWindow(request: SensorWindowRequest): Promise<WearableSensorWindow> { return parse(await fetch(`${API_BASE_URL}/api/v1/virtual-sensors/window`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) })); }
