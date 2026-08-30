export type MotionCondition = "STABLE_REST" | "ACTIVE_MOTION" | "POSTURE_TRANSITION";
export type ContactCondition = "NOMINAL_CONTACT" | "UNSTABLE_CONTACT" | "POOR_CONTACT";

export interface IMUSample { relative_time_seconds: number; acceleration_x_m_s2: number; acceleration_y_m_s2: number; acceleration_z_m_s2: number; angular_velocity_x_rad_s: number; angular_velocity_y_rad_s: number; angular_velocity_z_rad_s: number; roll_deg: number; pitch_deg: number; yaw_deg: number; }
export interface TemperatureSample { relative_time_seconds: number; temperature_c: number; }
export interface ContactSample { relative_time_seconds: number; contact_impedance_ohm: number; }
export interface BandSensorWindow { arm_side: "LEFT" | "RIGHT"; imu_sample_rate_hz: number; temperature_sample_rate_hz: number; contact_sample_rate_hz: number; imu_samples: IMUSample[]; temperature_samples: TemperatureSample[]; contact_samples: ContactSample[]; }
export interface WearableSensorWindow { window_id: string; window_index: number; simulation_id: string; anchor_simulated_time: string; anchor_wall_clock_time: string; duration_seconds: number; provenance: "SIMULATED"; source: "DIGITAL_TWIN"; qualification: "RAW_UNQUALIFIED"; motion_condition: MotionCondition; contact_condition: ContactCondition; temperature_offset_c: number; model_revision: string; left: BandSensorWindow; right: BandSensorWindow; }
export interface VirtualSensorConfiguration { model_name: string; model_revision: string; duration_seconds: number; imu_sample_rate_hz: number; temperature_sample_rate_hz: number; contact_sample_rate_hz: number; supported_motion_conditions: MotionCondition[]; supported_contact_conditions: ContactCondition[]; provenance: "SIMULATED"; source: "DIGITAL_TWIN"; qualification: "RAW_UNQUALIFIED"; }
