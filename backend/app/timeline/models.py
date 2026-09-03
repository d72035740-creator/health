from enum import Enum

from pydantic import AwareDatetime

from app.domain.models import ContractModel


class TimelineEventType(str, Enum):
    SYSTEM_RESET = "SYSTEM_RESET"
    BASELINE_CALIBRATION_STARTED = "BASELINE_CALIBRATION_STARTED"
    BASELINE_ESTABLISHED = "BASELINE_ESTABLISHED"
    SCENARIO_SELECTED = "SCENARIO_SELECTED"
    SCENARIO_STARTED = "SCENARIO_STARTED"
    SCENARIO_RESET = "SCENARIO_RESET"
    SIMULATION_TIME_ADVANCED = "SIMULATION_TIME_ADVANCED"
    MEASUREMENT_CYCLE_STARTED = "MEASUREMENT_CYCLE_STARTED"
    MEASUREMENT_QUALIFIED = "MEASUREMENT_QUALIFIED"
    MEASUREMENT_REJECTED = "MEASUREMENT_REJECTED"
    ML_INFERENCE_COMPLETED = "ML_INFERENCE_COMPLETED"
    TEMPORAL_STATE_CHANGED = "TEMPORAL_STATE_CHANGED"
    TEMPORAL_RESET = "TEMPORAL_RESET"
    SURVEILLANCE_STATE_CHANGED = "SURVEILLANCE_STATE_CHANGED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    RECOVERY_OBSERVED = "RECOVERY_OBSERVED"


class TimelineEventSource(str, Enum):
    SIMULATION_CONTROL = "SIMULATION_CONTROL"
    SCENARIO_ENGINE = "SCENARIO_ENGINE"
    QUALITY_ENGINE = "QUALITY_ENGINE"
    RUNTIME = "RUNTIME"
    ML_ENGINE = "ML_ENGINE"
    TEMPORAL_ENGINE = "TEMPORAL_ENGINE"
    DECISION_ENGINE = "DECISION_ENGINE"


class AequorTimelineEvent(ContractModel):
    event_id: str
    sequence_index: int
    simulated_time: AwareDatetime
    event_type: TimelineEventType
    source: TimelineEventSource
    title: str
    summary: str
    runtime_cycle_id: str | None = None
    scenario_ground_truth: dict[str, object] | None = None
    measurement_summary: dict[str, object] | None = None
    ml_summary: dict[str, object] | None = None
    temporal_summary: dict[str, object] | None = None
    confounder_summary: dict[str, object] | None = None
    decision_summary: dict[str, object] | None = None


class ReplaySession(ContractModel):
    session_id: str
    started_at_simulated_time: AwareDatetime
    event_count: int
    baseline_status: str
    starting_state: str
    current_state: str
    reset_boundary: str


class TimelineReplaySnapshot(ContractModel):
    title: str
    observer_only: bool
    ground_truth_disclosure: str
    session: ReplaySession
    duration_seconds: float
    measurement_count: int
    qualified_measurements: int
    rejected_measurements: int
    events: list[AequorTimelineEvent]
    trend_series: dict[str, list[dict[str, object]]]
    state_bands: list[dict[str, object]]
