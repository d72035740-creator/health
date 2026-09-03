from collections.abc import Callable

from fastapi import APIRouter, HTTPException, status

from app.simulation.clock import SimulationLifecycleError, SimulationValueError
from app.simulation.engine import simulation_engine
from app.simulation.models import ManualStepRequest, SimulationSnapshot, SpeedUpdate
from app.timeline.models import TimelineEventSource, TimelineEventType
from app.timeline.service import timeline_service


router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


def _perform(action: Callable[[], SimulationSnapshot]) -> SimulationSnapshot:
    try:
        return action()
    except SimulationLifecycleError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_SIMULATION_LIFECYCLE",
                "message": str(error),
                "lifecycle": error.lifecycle.value,
                "action": error.action,
            },
        ) from error
    except SimulationValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "INVALID_SIMULATION_VALUE", "message": str(error)},
        ) from error


@router.get("", response_model=SimulationSnapshot)
async def get_simulation() -> SimulationSnapshot:
    return simulation_engine.snapshot()


@router.post("/create", response_model=SimulationSnapshot)
async def create_simulation() -> SimulationSnapshot:
    return _perform(simulation_engine.create)


@router.post("/start", response_model=SimulationSnapshot)
async def start_simulation() -> SimulationSnapshot:
    return _perform(simulation_engine.start)


@router.post("/pause", response_model=SimulationSnapshot)
async def pause_simulation() -> SimulationSnapshot:
    return _perform(simulation_engine.pause)


@router.post("/resume", response_model=SimulationSnapshot)
async def resume_simulation() -> SimulationSnapshot:
    return _perform(simulation_engine.resume)


@router.post("/reset", response_model=SimulationSnapshot)
async def reset_simulation() -> SimulationSnapshot:
    return _perform(simulation_engine.reset)


@router.patch("/speed", response_model=SimulationSnapshot)
async def update_speed(request: SpeedUpdate) -> SimulationSnapshot:
    return _perform(lambda: simulation_engine.set_speed(request.speed_multiplier))


@router.post("/step", response_model=SimulationSnapshot)
async def step_simulation(request: ManualStepRequest) -> SimulationSnapshot:
    snapshot = _perform(lambda: simulation_engine.step(request.seconds))
    timeline_service.append(TimelineEventType.SIMULATION_TIME_ADVANCED,TimelineEventSource.SIMULATION_CONTROL,"Simulation time advanced",f"Advanced authoritative simulated time by {request.seconds:g} seconds.",simulated_time=snapshot.simulated_time)
    return snapshot
