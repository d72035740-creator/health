from datetime import datetime
from enum import Enum
from pydantic import AwareDatetime
from app.domain.models import ContractModel


class VerificationStatus(str,Enum): PASS='PASS';FAIL='FAIL';WARNING='WARNING';SKIPPED='SKIPPED'
class ReleaseStatus(str,Enum): READY='READY';READY_WITH_WARNINGS='READY_WITH_WARNINGS';NOT_READY='NOT_READY'
class VerificationCheck(ContractModel):
    check_id:str;title:str;category:str;status:VerificationStatus;critical:bool;duration_ms:float;evidence:dict[str,object];details:str;failure_reason:str|None=None
class VerificationSection(ContractModel):
    section_id:str;title:str;checks:list[VerificationCheck]
class VerificationReport(ContractModel):
    release_verification_revision:str;started_at:AwareDatetime;finished_at:AwareDatetime;git_commit:str|None;model_hash:str|None
    total_checks:int;passed:int;failed:int;warnings:int;skipped:int;overall_status:ReleaseStatus;sections:list[VerificationSection];scenario_summary:dict[str,object];known_warnings:list[str]


def overall_for(checks:list[VerificationCheck])->ReleaseStatus:
    if any(x.critical and x.status is VerificationStatus.FAIL for x in checks):return ReleaseStatus.NOT_READY
    if any(x.status in (VerificationStatus.WARNING,VerificationStatus.FAIL) for x in checks):return ReleaseStatus.READY_WITH_WARNINGS
    return ReleaseStatus.READY


def empty_report_status(status:VerificationStatus,critical:bool=True)->ReleaseStatus:
    check=VerificationCheck(check_id='test',title='test',category='test',status=status,critical=critical,duration_ms=0,evidence={},details='test')
    return overall_for([check])
