from fastapi import APIRouter, HTTPException, status
from app.baseline.service import BaselineError, baseline_service
from app.measurement import measurement_attempt_service
from app.scenario import scenario_provider, ScenarioType
from app.simulation.engine import simulation_engine
from app.simulation.sensors.models import SensorWindowRequest
from app.timeline.models import TimelineEventSource, TimelineEventType
from app.timeline.service import timeline_service

router=APIRouter(prefix="/api/v1/baseline",tags=["baseline"])

@router.get("/status")
async def baseline_status(): return baseline_service.snapshot()

@router.post("/start")
async def baseline_start():
    try:
        baseline_service.start(); timeline_service.append(TimelineEventType.BASELINE_CALIBRATION_STARTED,TimelineEventSource.RUNTIME,'Baseline calibration started','Qualified observations will establish the personal reference.'); return baseline_service.snapshot()
    except BaselineError as error: raise HTTPException(status_code=409,detail=str(error)) from error

@router.post("/capture")
async def baseline_capture(request: SensorWindowRequest=SensorWindowRequest()):
    if scenario_provider.state().active and scenario_provider.state().scenario_type is not ScenarioType.BASELINE_STABLE: raise HTTPException(status_code=409,detail="non-baseline scenario is active; baseline enrollment is blocked")
    try:
        attempt=measurement_attempt_service.attempt(request)
        if attempt.processed_features is None: raise BaselineError("measurement did not produce processed features")
        baseline_service.capture(attempt.processed_features); return baseline_service.snapshot()
    except BaselineError as error: raise HTTPException(status_code=409,detail=str(error)) from error

@router.post("/run-demo-calibration")
async def run_demo_calibration():
    if scenario_provider.state().scenario_type is not ScenarioType.BASELINE_STABLE or scenario_provider.state().active: raise HTTPException(status_code=409,detail="demo calibration requires BASELINE_STABLE with no active scenario")
    try:
        if baseline_service.snapshot().state.value=="UNINITIALIZED": baseline_service.start(); timeline_service.append(TimelineEventType.BASELINE_CALIBRATION_STARTED,TimelineEventSource.RUNTIME,'Baseline calibration started','Demo calibration began.')
        for index in range(28):
            attempt=measurement_attempt_service.attempt(SensorWindowRequest())
            if attempt.processed_features is None: raise BaselineError("demo measurement did not produce processed features")
            baseline_service.capture(attempt.processed_features)
            if index<27: simulation_engine.step(6*3600 if index<24 else 12*3600)
        baseline_service.finalize(); snapshot=baseline_service.snapshot(); timeline_service.append(TimelineEventType.BASELINE_ESTABLISHED,TimelineEventSource.RUNTIME,'Baseline established',f"Personal reference established from {snapshot.observation_count} qualified observations."); return snapshot
    except BaselineError as error: raise HTTPException(status_code=409,detail=str(error)) from error

@router.post("/finalize")
async def baseline_finalize():
    try:
        baseline_service.finalize(); snapshot=baseline_service.snapshot(); timeline_service.append(TimelineEventType.BASELINE_ESTABLISHED,TimelineEventSource.RUNTIME,'Baseline established',f"Personal reference established from {snapshot.observation_count} qualified observations."); return snapshot
    except BaselineError as error: raise HTTPException(status_code=409,detail=str(error)) from error

@router.post("/reset")
async def baseline_reset(): baseline_service.reset(); return baseline_service.snapshot()
