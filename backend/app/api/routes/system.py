import logging

from fastapi import APIRouter

from app.domain.enums import DataProvenance, PrototypeMode, SubsystemStatus
from app.domain.models import SystemStatus


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/status", response_model=SystemStatus)
async def system_status() -> SystemStatus:
    """Return authoritative availability only; never synthesize medical results."""
    logger.debug("System status requested")
    return SystemStatus(
        prototype_mode=PrototypeMode.SIMULATION,
        data_provenance=DataProvenance.SIMULATED,
        backend=SubsystemStatus.READY,
        digital_patient_engine=SubsystemStatus.READY,
        digital_twin=SubsystemStatus.NOT_IMPLEMENTED,
        bioimpedance_digital_twin=SubsystemStatus.READY,
        virtual_imu=SubsystemStatus.READY,
        virtual_temperature=SubsystemStatus.READY,
        virtual_contact=SubsystemStatus.READY,
        quality_engine=SubsystemStatus.NOT_IMPLEMENTED,
        signal_processing=SubsystemStatus.NOT_IMPLEMENTED,
        baseline_engine=SubsystemStatus.NOT_IMPLEMENTED,
        ml_engine=SubsystemStatus.NOT_IMPLEMENTED,
        temporal_engine=SubsystemStatus.NOT_IMPLEMENTED,
        confounder_engine=SubsystemStatus.NOT_IMPLEMENTED,
        decision_engine=SubsystemStatus.NOT_IMPLEMENTED,
    )
