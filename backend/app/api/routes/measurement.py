from fastapi import APIRouter, HTTPException, status
from app.measurement import measurement_attempt_service
from app.quality.config import public_thresholds
from app.quality.models import MeasurementAttempt
from app.simulation.sensors.models import SensorWindowRequest
from app.simulation.sensors.service import VirtualSensorsUnavailableError
from app.signal_processing.config import processing_config
from app.ml.runtime import ml_runtime
from app.temporal.service import temporal_service
from app.temporal.config import public_config as temporal_config
from app.confounders.service import confounder_service
from app.decision.service import decision_service
from app.runtime import runtime_service, RuntimeBusyError
from app.timeline.models import TimelineEventSource, TimelineEventType
from app.timeline.service import timeline_service

router=APIRouter(prefix="/api/v1", tags=["measurement-quality"])

@router.get("/ml/status")
async def ml_status() -> dict[str, object]: return ml_runtime.status()

@router.get("/ml/model")
async def ml_model() -> dict[str, object]: return ml_runtime.status()

@router.get('/temporal/status')
async def temporal_status(): return temporal_service.assessment()
@router.get('/temporal/history')
async def temporal_history(): return temporal_service.history()
@router.post('/temporal/reset')
async def temporal_reset():
 temporal_service.reset(); confounder_service.reset(); timeline_service.append(TimelineEventType.TEMPORAL_RESET,TimelineEventSource.TEMPORAL_ENGINE,'Temporal evidence reset','Temporal service reset; recorded prior replay events were retained.'); return temporal_service.assessment()
@router.get('/temporal/config')
async def get_temporal_config(): return temporal_config()
@router.get('/confounders/config')
async def confounders_config(): return {'confounder_engine_name':'Aequor Confounder Reasoning Engine','confounder_revision':'confounder-v1'}
@router.get('/confounders/latest')
async def confounders_latest(): return confounder_service.latest()
@router.get('/decision/config')
async def decision_config():
 from app.decision.config import public_config
 return public_config()
@router.get('/decision/latest')
async def decision_latest(): return decision_service.latest()
@router.get('/runtime/status')
async def runtime_status(): return runtime_service.status()
@router.get('/runtime/snapshot')
async def runtime_snapshot(): return runtime_service.snapshot()
@router.get('/runtime/history')
async def runtime_history(): return runtime_service.history()
@router.post('/runtime/measure')
async def runtime_measure(request: SensorWindowRequest):
 try: return runtime_service.measure(request)
 except RuntimeBusyError as error: raise HTTPException(status_code=409,detail={'code':'RUNTIME_BUSY','message':str(error)}) from error

@router.get("/signal-processing/config")
async def get_signal_processing_config() -> dict[str, object]: return processing_config()

@router.get("/quality/config")
async def get_quality_config() -> dict[str, object]: return public_thresholds()

@router.post("/measurement/attempt", response_model=MeasurementAttempt)
async def attempt_measurement(request: SensorWindowRequest) -> MeasurementAttempt:
    try: return measurement_attempt_service.attempt(request)
    except VirtualSensorsUnavailableError as error: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code":"MEASUREMENT_UNAVAILABLE","message":str(error)}) from error
