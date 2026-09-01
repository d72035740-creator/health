import type { ContactCondition, MotionCondition, WearableSensorWindow } from "@/lib/types/virtual-sensors";
import type { ProcessedFeatures } from "@/lib/types/signal-processing";
export interface MeasurementAttempt { attempt_id:string; attempt_index:number; simulated_time:string; sensor_window:WearableSensorWindow; quality_assessment:{ qualification:"QUALIFIED"|"REJECTED"; overall_score:number; dimension_scores:Record<string,number>; rejection_reasons:string[]; explanation:string; }; bis_sweep:{ sweep_index:number }|null; processed_features:ProcessedFeatures|null; }
export type MeasurementAttemptRequest={motion_condition:MotionCondition;contact_condition:ContactCondition;temperature_offset_c:number};
