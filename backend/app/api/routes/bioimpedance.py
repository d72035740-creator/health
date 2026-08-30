from fastapi import APIRouter, HTTPException, status

from app.simulation.bioimpedance.models import (
    BioimpedanceTwinConfiguration,
    BilateralBioimpedanceSweep,
)
from app.simulation.bioimpedance.service import (
    BioimpedanceUnavailableError,
    bioimpedance_service,
)


router = APIRouter(prefix="/api/v1/bioimpedance", tags=["bioimpedance"])


@router.get("/config", response_model=BioimpedanceTwinConfiguration)
async def get_bioimpedance_configuration() -> BioimpedanceTwinConfiguration:
    return bioimpedance_service.configuration()


@router.post("/sweep", response_model=BilateralBioimpedanceSweep)
async def acquire_bilateral_sweep() -> BilateralBioimpedanceSweep:
    try:
        return bioimpedance_service.acquire()
    except BioimpedanceUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "BIOIMPEDANCE_UNAVAILABLE", "message": str(error)},
        ) from error

