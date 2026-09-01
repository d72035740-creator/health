from enum import Enum
from pydantic import AwareDatetime
from app.domain.models import ContractModel
class SurveillanceState(str,Enum): CALIBRATING='CALIBRATING'; WITHIN_PERSONAL_BASELINE='WITHIN_PERSONAL_BASELINE'; OBSERVING_CHANGE='OBSERVING_CHANGE'; PERSISTENT_DEVIATION='PERSISTENT_DEVIATION'; CLINICAL_REVIEW_RECOMMENDED='CLINICAL_REVIEW_RECOMMENDED'
class DecisionSnapshot(ContractModel):
    decision_engine_name:str; adi_revision:str; state_machine_revision:str; simulated_time:AwareDatetime; adi:float|None
    components:dict[str,float]|None; modifiers:dict[str,float]|None; surveillance_state:SurveillanceState; dominant_observed_side:str|None
    explanation_codes:list[str]; explanations:list[str]; evidence_revisions:dict[str,str]
class StateTransitionEvent(ContractModel):
    state_transition_id:str; simulated_time:AwareDatetime; from_state:SurveillanceState; to_state:SurveillanceState; adi:float|None; reason_codes:list[str]; evidence_revisions:dict[str,str]
