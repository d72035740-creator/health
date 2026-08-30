from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.enums import ArmSide
from app.domain.models import (
    BioimpedanceSweep,
    ContactQualitySample,
    IMUSample,
    TemperatureSample,
)


@runtime_checkable
class BioimpedanceSource(Protocol):
    def acquire_sweep(
        self,
        *,
        arm_side: ArmSide,
        simulation_id: str,
        sweep_index: int,
        wall_clock_time: datetime,
        simulated_time: datetime,
    ) -> BioimpedanceSweep: ...


@runtime_checkable
class MotionSource(Protocol):
    async def acquire_sample(self, arm_side: ArmSide) -> IMUSample: ...


@runtime_checkable
class TemperatureSource(Protocol):
    async def acquire_sample(self, arm_side: ArmSide) -> TemperatureSample: ...


@runtime_checkable
class ContactQualitySource(Protocol):
    async def acquire_sample(self, arm_side: ArmSide) -> ContactQualitySample: ...


# Phase 3 sources use raw contact impedance rather than interpreted quality.
# The concrete window-oriented protocols live beside the virtual sensor service,
# avoiding a dependency from the Phase 0 domain boundary onto Phase 3 contracts.
