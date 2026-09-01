from datetime import datetime
from enum import Enum
from pydantic import AwareDatetime, Field
from app.domain.models import ContractModel

class TemporalEvidenceState(str, Enum):
    INSUFFICIENT_HISTORY='INSUFFICIENT_HISTORY'; STABLE_PATTERN='STABLE_PATTERN'; TRANSIENT_ELEVATION='TRANSIENT_ELEVATION'; SUSTAINED_ELEVATION='SUSTAINED_ELEVATION'; RISING_PERSISTENT_PATTERN='RISING_PERSISTENT_PATTERN'; RECOVERING_PATTERN='RECOVERING_PATTERN'

class TemporalObservation(ContractModel):
    observation_id:str; measurement_attempt_id:str; simulated_time:AwareDatetime
    reconstruction_error_mse:float; novelty_z:float; model_novelty_score:float
    model_revision:str; baseline_revision:str; feature_revision:str

class TemporalAssessment(ContractModel):
    temporal_revision:str; observation_count:int; history_start_time:AwareDatetime|None; latest_time:AwareDatetime|None
    latest_novelty_z:float|None; ewma_novelty:float|None; cusum_value:float; cusum_engineering_threshold:float; cusum_exceeded:bool
    elevated_observation_count:int; persistence_duration_seconds:float; persistence_duration_days:float
    recent_novelty_slope_per_day:float|None; temporal_state:TemporalEvidenceState
