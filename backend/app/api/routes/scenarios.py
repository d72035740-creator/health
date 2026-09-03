from fastapi import APIRouter, HTTPException
from pydantic import Field
from app.domain.enums import ArmSide
from app.domain.models import ContractModel
from app.scenario import ScenarioType, scenario_provider
from app.timeline.models import TimelineEventSource, TimelineEventType
from app.timeline.service import timeline_service

class ScenarioSelection(ContractModel): scenario_type: ScenarioType; affected_arm: ArmSide|None=None
router=APIRouter(prefix="/api/v1/scenarios",tags=["scenarios"])
@router.get("/config")
async def config(): return {"scenario_engine_name":"Aequor Longitudinal Scenario Engine","scenario_revision":"scenario-v1","scenario_types":[x.value for x in ScenarioType],"severity_semantics":"Synthetic scenario progression in [0,1]; engineering ground truth only."}
@router.get("/state")
async def state(): return scenario_provider.state().as_dict()
@router.post("/select")
async def select(request:ScenarioSelection):
 scenario_provider.select(request.scenario_type,request.affected_arm); state=scenario_provider.state().as_dict(); timeline_service.append(TimelineEventType.SCENARIO_SELECTED,TimelineEventSource.SCENARIO_ENGINE,'Scenario selected',f"Selected {request.scenario_type.value}.",scenario_ground_truth=state); return state
@router.post("/start")
async def start():
 scenario_provider.start(); state=scenario_provider.state().as_dict(); timeline_service.append(TimelineEventType.SCENARIO_STARTED,TimelineEventSource.SCENARIO_ENGINE,'Scenario started',f"Started {state['scenario_type']}.",scenario_ground_truth=state); return state
@router.post("/reset")
async def reset():
 before=scenario_provider.state().as_dict(); timeline_service.append(TimelineEventType.SCENARIO_RESET,TimelineEventSource.SCENARIO_ENGINE,'Scenario reset',f"Reset {before['scenario_type']}; prior replay history retained.",scenario_ground_truth=before); scenario_provider.reset(); return scenario_provider.state().as_dict()
