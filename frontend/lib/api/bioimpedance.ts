import type {
  BilateralBioimpedanceSweep,
  BioimpedanceTwinConfiguration,
} from "@/lib/types/bioimpedance";


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Bioimpedance request failed with HTTP ${response.status}`;
    try {
      const body = await response.json() as { detail?: { message?: string } | string };
      message = typeof body.detail === "string" ? body.detail : body.detail?.message ?? message;
    } catch {
      // Keep the HTTP fallback for non-JSON proxy/server errors.
    }
    throw new Error(message);
  }
  return await response.json() as T;
}


export async function fetchBioimpedanceConfig(signal?: AbortSignal): Promise<BioimpedanceTwinConfiguration> {
  return parseResponse(await fetch(`${API_BASE_URL}/api/v1/bioimpedance/config`, {
    cache: "no-store",
    signal,
  }));
}


export async function acquireBilateralSweep(): Promise<BilateralBioimpedanceSweep> {
  return parseResponse(await fetch(`${API_BASE_URL}/api/v1/bioimpedance/sweep`, {
    method: "POST",
  }));
}

