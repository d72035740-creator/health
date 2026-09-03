from fastapi import APIRouter
from app.views.service import patient_view_service,clinician_view_service,engineering_view_service,lab_view_service,digital_twin_inspector_service,timeline_replay_view_service
from app.views.models import PatientViewSnapshot,ClinicianViewSnapshot,EngineeringViewSnapshot,LabViewSnapshot,DigitalTwinInspectorSnapshot
from app.timeline.models import TimelineReplaySnapshot
router=APIRouter(prefix='/api/v1/views',tags=['presentation-views'])
@router.get('/patient',response_model=PatientViewSnapshot)
async def patient_view(): return patient_view_service.snapshot()
@router.get('/clinician',response_model=ClinicianViewSnapshot)
async def clinician_view(): return clinician_view_service.snapshot()
@router.get('/engineering',response_model=EngineeringViewSnapshot)
async def engineering_view(): return engineering_view_service.snapshot()
@router.get('/lab',response_model=LabViewSnapshot)
async def lab_view(): return lab_view_service.snapshot()
@router.get('/digital-twin',response_model=DigitalTwinInspectorSnapshot)
async def digital_twin_view(): return digital_twin_inspector_service.snapshot()
@router.get('/timeline',response_model=TimelineReplaySnapshot)
async def timeline_view(include_ground_truth:bool=True): return timeline_replay_view_service.snapshot(include_ground_truth)
