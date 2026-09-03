from pydantic import AwareDatetime
from app.domain.models import ContractModel

class PatientTrendPoint(ContractModel): simulated_time:AwareDatetime; relative_balance_value:float
class PatientMeasurementSummary(ContractModel): total_recent_attempts:int; qualified_recent_attempts:int; rejected_recent_attempts:int
class PatientViewSnapshot(ContractModel):
    synthetic_patient:dict[str,object]; prototype_disclosure:str; surveillance_state:str; state_title:str; state_message:str
    baseline:dict[str,object]; latest_measurement:dict[str,object]|None; fluid_balance_summary:dict[str,object]|None
    trend:list[PatientTrendPoint]; measurement_summary:PatientMeasurementSummary; privacy_summary:dict[str,str]; recommended_message:str
class ClinicianTrendPoint(ContractModel): simulated_time:AwareDatetime; left_relative_index:float; right_relative_index:float; adi:float|None; surveillance_state:str|None
class ClinicianViewSnapshot(ContractModel):
    patient:dict[str,object]; prototype_disclosure:str; surveillance_state:str; adi:float|None; adi_label:str; adi_revision:str
    dominant_observed_side:str|None; latest_measurement:dict[str,object]|None; quality_summary:dict[str,object]
    bilateral_summary:dict[str,object]|None; spectral_summary:list[dict[str,object]]; baseline_summary:dict[str,object]
    temporal_summary:dict[str,object]|None; confounder_summary:dict[str,object]|None; decision_components:dict[str,float]|None
    decision_modifiers:dict[str,float]|None; explanations:list[str]; longitudinal_trend:list[ClinicianTrendPoint]
    state_history:list[dict[str,object]]; model_metadata_summary:dict[str,object]
class EngineeringViewSnapshot(ContractModel):
    header:dict[str,object]; pipeline:list[dict[str,object]]; latest_cycle:dict[str,object]|None; technical_acquisition:dict[str,object]|None
    bis:dict[str,object]|None; signal_processing:dict[str,object]|None; baseline:dict[str,object]; tinyml:dict[str,object]
    temporal:dict[str,object]|None; temporal_history:list[dict[str,object]]; confounders:dict[str,object]|None; decision:dict[str,object]|None
    adi_configuration:dict[str,object]; system_health:dict[str,object]; provenance:dict[str,list[str]]
class LabViewSnapshot(ContractModel):
    simulation:dict[str,object]; scenario_ground_truth:dict[str,object]; baseline:dict[str,object]; runtime:dict[str,object]
    observed_evidence:dict[str,object]|None; event_feed:list[dict[str,object]]; disclosure:str


class DigitalTwinParameterModifier(ContractModel):
    delta_r_zero_ohm: float
    delta_r_infinity_ohm: float
    delta_tau_seconds: float
    delta_beta: float


class DigitalTwinArmParameters(ContractModel):
    arm: str
    base: dict[str, float]
    effective: dict[str, float]
    modifier: DigitalTwinParameterModifier


class DigitalTwinSpectrumPoint(ContractModel):
    frequency_hz: float
    resistance_ohm: float
    reactance_ohm: float
    magnitude_ohm: float
    phase_deg: float


class DigitalTwinEvolutionPoint(ContractModel):
    progression: float
    left: dict[str, float]
    right: dict[str, float]


class DigitalTwinFitComparison(ContractModel):
    parameter: str
    arm: str
    ground_truth_value: float
    processor_estimate: float | None
    difference: float | None
    fit_available: bool


class VirtualSensorInspectorSummary(ContractModel):
    available: bool
    simulated_data: bool = True
    motion_condition: str | None = None
    posture_condition: str | None = None
    gravity_projection_m_s2: dict[str, float] | None = None
    motion_level_rad_s: dict[str, float] | None = None
    skin_temperature_c: dict[str, float] | None = None
    contact_impedance_ohm: dict[str, float] | None = None
    technical_quality: str | None = None
    quality_score: float | None = None
    technical_details: dict[str, object] | None = None


class DigitalTwinInspectorSnapshot(ContractModel):
    title: str
    provenance_label: str
    disclosure: str
    equation: dict[str, str]
    scenario_ground_truth: dict[str, object]
    arm_parameters: list[DigitalTwinArmParameters]
    parameter_evolution: list[DigitalTwinEvolutionPoint]
    model_prediction: dict[str, list[DigitalTwinSpectrumPoint]]
    latest_acquired_sweep: dict[str, object] | None
    fit_comparison: list[DigitalTwinFitComparison]
    virtual_sensors: VirtualSensorInspectorSummary
    anti_leakage: dict[str, object]
    noise_explanation: list[str]
