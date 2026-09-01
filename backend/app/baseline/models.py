from enum import Enum
from pydantic import AwareDatetime, Field
from app.domain.models import ContractModel
from app.signal_processing.models import ProcessedBioimpedanceFeatures

class BaselineLifecycle(str, Enum): UNINITIALIZED="UNINITIALIZED"; CALIBRATING="CALIBRATING"; READY="READY"
class BaselineFeatureStatistics(ContractModel):
    name:str; count:int; median:float; mad:float; q1:float; q3:float; iqr:float; robust_scale:float
class BaselineComparisonValue(ContractModel):
    name:str; current_value:float; baseline_median:float; baseline_scale:float; signed_normalized_delta:float
class BaselineComparison(ContractModel):
    feature_revision:str; values:list[BaselineComparisonValue]
class PersonalizedBaselineSnapshot(ContractModel):
    state:BaselineLifecycle; baseline_engine_name:str; baseline_revision:str; feature_revision:str; observation_count:int; minimum_observations:int; simulated_span_seconds:float; minimum_simulated_span_seconds:float; statistics:list[BaselineFeatureStatistics]
