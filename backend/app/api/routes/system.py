import logging

from fastapi import APIRouter

from app.domain.enums import DataProvenance, PrototypeMode, SubsystemStatus
from app.domain.models import SystemStatus
from app.ml.runtime import ml_runtime
from app.temporal.service import temporal_service
from app.confounders.service import confounder_service


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
        quality_engine=SubsystemStatus.READY,
        signal_processing=SubsystemStatus.READY,
        baseline_engine=SubsystemStatus.READY,
        scenario_engine=SubsystemStatus.READY,
        ml_engine=SubsystemStatus.READY if ml_runtime._interpreter is not None else SubsystemStatus.ERROR,
        temporal_engine=SubsystemStatus.READY,
        confounder_engine=SubsystemStatus.READY,
        decision_engine=SubsystemStatus.READY,
    )
