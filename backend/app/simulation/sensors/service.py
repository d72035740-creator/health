from threading import RLock

from app.domain.enums import ArmSide, DataProvenance, SimulationLifecycle
from app.simulation.bioimpedance.models import AcquisitionQualification
from app.simulation.engine import DigitalPatientEngine, simulation_engine
from app.simulation.sensors.config import default_configuration
from app.simulation.sensors.models import BandSensorWindow, SensorWindowRequest, VirtualSensorConfiguration, VirtualSensorSourceType, WearableSensorWindow
from app.simulation.sensors.source import ContactSource, DigitalTwinContactSource, DigitalTwinMotionSource, DigitalTwinTemperatureSource, MotionSource, TemperatureSource


class VirtualSensorsUnavailableError(RuntimeError):
    pass


class WearableSensorService:
    def __init__(self, *, engine: DigitalPatientEngine, configuration: VirtualSensorConfiguration | None = None, motion_source: MotionSource | None = None, temperature_source: TemperatureSource | None = None, contact_source: ContactSource | None = None) -> None:
        self._lock = RLock(); self._engine = engine; self._configuration = configuration or default_configuration()
        self._motion_source = motion_source or DigitalTwinMotionSource(engine.random_source)
        self._temperature_source = temperature_source or DigitalTwinTemperatureSource(engine.random_source)
        self._contact_source = contact_source or DigitalTwinContactSource(engine.random_source)
        self._window_index = 0
        engine.register_reset_hook(self.reset)

    def configuration(self) -> VirtualSensorConfiguration:
        return self._configuration

    def reset(self) -> None:
        with self._lock: self._window_index = 0

    def acquire(self, request: SensorWindowRequest) -> WearableSensorWindow:
        snapshot = self._engine.snapshot()
        if snapshot.lifecycle is SimulationLifecycle.UNINITIALIZED:
            raise VirtualSensorsUnavailableError("Digital Patient simulation is uninitialized")
        with self._lock:
            self._window_index += 1; index = self._window_index; cfg = self._configuration
            def band(arm: ArmSide) -> BandSensorWindow:
                return BandSensorWindow(arm_side=arm, imu_sample_rate_hz=cfg.imu_sample_rate_hz, temperature_sample_rate_hz=cfg.temperature_sample_rate_hz, contact_sample_rate_hz=cfg.contact_sample_rate_hz,
                    imu_samples=self._motion_source.acquire_samples(arm_side=arm, window_index=index, condition=request.motion_condition, duration_seconds=cfg.duration_seconds, sample_rate_hz=cfg.imu_sample_rate_hz),
                    temperature_samples=self._temperature_source.acquire_samples(arm_side=arm, window_index=index, offset_c=request.temperature_offset_c, duration_seconds=cfg.duration_seconds, sample_rate_hz=cfg.temperature_sample_rate_hz),
                    contact_samples=self._contact_source.acquire_samples(arm_side=arm, window_index=index, condition=request.contact_condition, duration_seconds=cfg.duration_seconds, sample_rate_hz=cfg.contact_sample_rate_hz))
            return WearableSensorWindow(window_id=f"{snapshot.simulation_id}:sensor-window:{index}", window_index=index, simulation_id=snapshot.simulation_id,
                anchor_simulated_time=snapshot.simulated_time, anchor_wall_clock_time=snapshot.wall_clock_time, duration_seconds=cfg.duration_seconds,
                provenance=DataProvenance.SIMULATED, source=VirtualSensorSourceType.DIGITAL_TWIN, qualification=AcquisitionQualification.RAW_UNQUALIFIED,
                motion_condition=request.motion_condition, contact_condition=request.contact_condition, temperature_offset_c=request.temperature_offset_c, model_revision=cfg.model_revision, left=band(ArmSide.LEFT), right=band(ArmSide.RIGHT))


wearable_sensor_service = WearableSensorService(engine=simulation_engine)
