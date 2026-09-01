import type { MeasurementAttempt, MeasurementAttemptRequest } from "@/lib/types/measurement";
const BASE=process.env.NEXT_PUBLIC_API_BASE_URL??"http://localhost:8000";
export async function attemptMeasurement(request:MeasurementAttemptRequest):Promise<MeasurementAttempt>{const response=await fetch(`${BASE}/api/v1/measurement/attempt`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(request)});if(!response.ok)throw new Error("Measurement attempt unavailable.");return response.json() as Promise<MeasurementAttempt>;}
