export type SubsystemStatus = "READY" | "NOT_IMPLEMENTED" | "DISCONNECTED" | "ERROR";
export type DataProvenance = "SIMULATED" | "HARDWARE";
export type ConnectionState = "CONNECTED" | "CONNECTING" | "DISCONNECTED";

export interface SystemStatus {
  prototype_mode: "SIMULATION";
  data_provenance: DataProvenance;
  backend: SubsystemStatus;
  digital_patient_engine: SubsystemStatus;
  digital_twin: SubsystemStatus;
  bioimpedance_digital_twin: SubsystemStatus;
  virtual_imu: SubsystemStatus;
  virtual_temperature: SubsystemStatus;
  virtual_contact: SubsystemStatus;
  quality_engine: SubsystemStatus;
  signal_processing: SubsystemStatus;
  baseline_engine: SubsystemStatus;
  ml_engine: SubsystemStatus;
  temporal_engine: SubsystemStatus;
  confounder_engine: SubsystemStatus;
  decision_engine: SubsystemStatus;
}

export interface SystemHeartbeat {
  type: "system.heartbeat";
  timestamp: string;
  backend_status: SubsystemStatus;
}
