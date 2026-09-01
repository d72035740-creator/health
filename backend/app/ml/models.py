from pydantic import AwareDatetime, Field
from app.domain.enums import DataProvenance, SubsystemStatus
from app.domain.models import ContractModel
class MLInferenceResult(ContractModel):
    status:SubsystemStatus; model_name:str|None=None; model_revision:str|None=None; ml_input_revision:str|None=None; feature_revision:str|None=None; inference_runtime:str|None=None; reconstruction_error_mse:float|None=None; novelty_z:float|None=None; model_novelty_score:float|None=None; inference_latency_ms:float|None=None; input_dimension:int|None=None; model_size_bytes:int|None=None; provenance:DataProvenance|None=None; error:str|None=None
