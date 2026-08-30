from fastapi import APIRouter, HTTPException, status

from app.simulation.sensors.models import SensorWindowRequest, VirtualSensorConfiguration, WearableSensorWindow
from app.simulation.sensors.service import VirtualSensorsUnavailableError, wearable_sensor_service

router = APIRouter(prefix="/api/v1/virtual-sensors", tags=["virtual-sensors"])

@router.get("/config", response_model=VirtualSensorConfiguration)
async def get_virtual_sensor_configuration() -> VirtualSensorConfiguration:
    return wearable_sensor_service.configuration()

@router.post("/window", response_model=WearableSensorWindow)
async def acquire_sensor_window(request: SensorWindowRequest) -> WearableSensorWindow:
    try:
        return wearable_sensor_service.acquire(request)
    except VirtualSensorsUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "VIRTUAL_SENSORS_UNAVAILABLE", "message": str(error)}) from error
