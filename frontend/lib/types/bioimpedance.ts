export interface ColeModelParameters {
  r_zero_ohm: number;
  r_infinity_ohm: number;
  tau_seconds: number;
  beta: number;
}

export interface BioimpedanceFrequencyPoint {
  frequency_hz: number;
  resistance_ohm: number;
  reactance_ohm: number;
  magnitude_ohm: number;
  phase_deg: number;
}

export interface BioimpedanceSweep {
  sample_id: string;
  arm_side: "LEFT" | "RIGHT";
  provenance: "SIMULATED";
  wall_clock_time: string;
  simulated_time: string;
  points: BioimpedanceFrequencyPoint[];
}

export interface BilateralBioimpedanceSweep {
  pair_id: string;
  sweep_index: number;
  simulation_id: string;
  simulated_time: string;
  wall_clock_time: string;
  provenance: "SIMULATED";
  source: "DIGITAL_TWIN";
  qualification: "RAW_UNQUALIFIED";
  model_revision: string;
  left: BioimpedanceSweep;
  right: BioimpedanceSweep;
}

export interface BioimpedanceTwinConfiguration {
  model_name: string;
  model_revision: string;
  frequencies_hz: number[];
  provenance: "SIMULATED";
  source: "DIGITAL_TWIN";
  qualification: "RAW_UNQUALIFIED";
  noise: {
    enabled: boolean;
    relative_bound: number;
  };
  left_parameters: ColeModelParameters;
  right_parameters: ColeModelParameters;
}

