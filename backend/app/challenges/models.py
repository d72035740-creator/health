from enum import Enum
from pydantic import AwareDatetime
from app.domain.models import ContractModel


class ChallengeStatus(str,Enum): PASS='PASS'; FAIL='FAIL'; INCONCLUSIVE='INCONCLUSIVE'
class ChallengeDefinition(ContractModel):
    challenge_id:str; title:str; question:str; naive_failure_mode:str; expected_invariant:str
class ChallengeEvidence(ContractModel):
    observations:dict[str,object]; invariant_checks:dict[str,bool|None]
class ChallengeResult(ContractModel):
    challenge_id:str; title:str; run_time:AwareDatetime; simulated_start:AwareDatetime; simulated_end:AwareDatetime
    status:ChallengeStatus; observed_evidence:ChallengeEvidence; expected_invariant:str; explanation:str; runtime_cycle_ids:list[str]
class ChallengeSuiteSnapshot(ContractModel):
    definitions:list[ChallengeDefinition]; latest_results:list[ChallengeResult]; history_count:int
