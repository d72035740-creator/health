from enum import Enum
from app.domain.models import ContractModel
class DominantChangeSide(str,Enum): LEFT='LEFT'; RIGHT='RIGHT'; BALANCED='BALANCED'; UNDETERMINED='UNDETERMINED'
class ConfounderAssessment(ContractModel):
    confounder_revision:str; bilateral_coherence_score:float; unilateral_asymmetry_score:float; dominant_change_side:DominantChangeSide
    systemic_bilateral_evidence:float; temperature_association_evidence:float; residual_motion_evidence:float; residual_contact_evidence:float; transient_pattern_evidence:float
    explanations:list[dict[str,str]]
