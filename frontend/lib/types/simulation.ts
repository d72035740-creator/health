import type { ConnectionState, DataProvenance } from "@/lib/types/system";


export type SimulationLifecycle = "UNINITIALIZED" | "READY" | "RUNNING" | "PAUSED";

export interface SyntheticPatient {
  patient_id: string;
  display_name: string;
  age_years: number;
  sex: "FEMALE" | "MALE" | "OTHER" | "UNSPECIFIED";
  dominant_arm: "LEFT" | "RIGHT";
  created_at: string;
  synthetic: true;
}

export interface SimulationSnapshot {
  simulation_id: string;
  patient: SyntheticPatient;
  seed: number;
  lifecycle: SimulationLifecycle;
  wall_clock_time: string;
  simulated_time: string;
  speed_multiplier: number;
  data_provenance: Extract<DataProvenance, "SIMULATED">;
}

export interface SimulationClockEvent {
  type: "simulation.clock";
  simulation_id: string;
  lifecycle: SimulationLifecycle;
  wall_clock_time: string;
  simulated_time: string;
  speed_multiplier: number;
}

export type SimulationConnectionState = ConnectionState;
export type SimulationAction = "create" | "start" | "pause" | "resume" | "reset";

