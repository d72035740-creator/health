from datetime import datetime
from enum import Enum
from threading import RLock

from app.domain.enums import ArmSide
from app.simulation.bioimpedance.models import ColeModelParameters
from app.simulation.engine import DigitalPatientEngine, simulation_engine


class ScenarioType(str, Enum):
    BASELINE_STABLE = "BASELINE_STABLE"
    SYSTEMIC_BILATERAL_SHIFT = "SYSTEMIC_BILATERAL_SHIFT"
    TRANSIENT_UNILATERAL_SHIFT = "TRANSIENT_UNILATERAL_SHIFT"
    SLOW_UNILATERAL_SHIFT = "SLOW_UNILATERAL_SHIFT"
    RAPID_UNILATERAL_SHIFT = "RAPID_UNILATERAL_SHIFT"
    RECOVERY = "RECOVERY"


SCENARIO_ENGINE_NAME = "Aequor Longitudinal Scenario Engine"
SCENARIO_REVISION = "scenario-v1"


class ScenarioSelection(dict):
    pass


class ScenarioState:
    def __init__(self) -> None:
        self.scenario_id = "scenario-0"
        self.scenario_type = ScenarioType.BASELINE_STABLE
        self.affected_arm: ArmSide | None = None
        self.start_simulated_time: datetime | None = None
        self.elapsed_simulated_time = 0.0
        self.severity = 0.0
        self.active = False

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type.value,
            "affected_arm": self.affected_arm.value if self.affected_arm else None,
            "start_simulated_time": self.start_simulated_time,
            "elapsed_simulated_time": self.elapsed_simulated_time,
            "severity": self.severity,
            "scenario_revision": SCENARIO_REVISION,
            "scenario_engine_name": SCENARIO_ENGINE_NAME,
            "active": self.active,
        }


class ScenarioProvider:
    def __init__(self, engine: DigitalPatientEngine) -> None:
        self._engine = engine
        self._lock = RLock()
        self._state = ScenarioState()
        engine.register_reset_hook(self.reset)

    def state(self) -> ScenarioState:
        with self._lock:
            self._refresh()
            return self._state

    def select(self, scenario_type: ScenarioType, affected_arm: ArmSide | None = None) -> None:
        with self._lock:
            self._state.scenario_type = scenario_type
            self._state.affected_arm = affected_arm
            self._state.start_simulated_time = None
            self._state.elapsed_simulated_time = 0.0
            self._state.active = False
            self._state.severity = 0.0

    def start(self) -> None:
        with self._lock:
            self._state.start_simulated_time = self._engine.snapshot().simulated_time
            self._state.active = True
            self._state.severity = 0.0

    def reset(self) -> None:
        with self._lock:
            self._state = ScenarioState()

    @staticmethod
    def progression_for(kind: ScenarioType, elapsed_seconds: float) -> float:
        elapsed = max(0.0, elapsed_seconds)
        if kind is ScenarioType.TRANSIENT_UNILATERAL_SHIFT:
            phase = min(1.0, elapsed / 172_800)
            return 2 * phase if phase < 0.5 else 2 * (1 - phase)
        if kind is ScenarioType.RAPID_UNILATERAL_SHIFT:
            return min(1.0, elapsed / 172_800)
        return min(1.0, elapsed / (7 * 86_400))

    def _refresh(self) -> None:
        state = self._state
        if not state.active or state.start_simulated_time is None:
            return
        now = self._engine.snapshot().simulated_time
        state.elapsed_simulated_time = max(0.0, (now - state.start_simulated_time).total_seconds())
        state.severity = self.progression_for(state.scenario_type, state.elapsed_simulated_time)

    @staticmethod
    def _apply_modifier(
        *, kind: ScenarioType, affected_arm: ArmSide | None, arm: ArmSide,
        progression: float, base: ColeModelParameters, active: bool,
    ) -> ColeModelParameters:
        if kind is ScenarioType.BASELINE_STABLE or not active:
            return base
        if kind is not ScenarioType.SYSTEMIC_BILATERAL_SHIFT and affected_arm is not arm:
            return base
        bounded = max(0.0, min(1.0, progression))
        magnitude = bounded * max(0.0, 1 - bounded) if kind is ScenarioType.RECOVERY else bounded
        if kind is ScenarioType.SYSTEMIC_BILATERAL_SHIFT:
            magnitude = 0.12 * bounded
        return ColeModelParameters(
            r_zero_ohm=base.r_zero_ohm * (1 + 0.18 * magnitude),
            r_infinity_ohm=base.r_infinity_ohm * (1 + 0.10 * magnitude),
            tau_seconds=base.tau_seconds * (1 + 0.45 * magnitude),
            beta=max(0.05, min(1.0, base.beta - 0.08 * magnitude)),
        )

    def effective_parameters(self, arm: ArmSide, simulated_time: datetime, base: ColeModelParameters) -> ColeModelParameters:
        with self._lock:
            state = self._state
            progression = state.severity
            if state.active and state.start_simulated_time is not None:
                progression = self.progression_for(
                    state.scenario_type, (simulated_time - state.start_simulated_time).total_seconds()
                )
            return self._apply_modifier(
                kind=state.scenario_type, affected_arm=state.affected_arm, arm=arm,
                progression=progression, base=base, active=state.active,
            )

    def preview_parameters(self, arm: ArmSide, base: ColeModelParameters, progression: float) -> ColeModelParameters:
        """Read-only preview through the exact modifier path used by acquisition."""
        with self._lock:
            return self._apply_modifier(
                kind=self._state.scenario_type, affected_arm=self._state.affected_arm,
                arm=arm, progression=progression, base=base, active=self._state.active,
            )


scenario_provider = ScenarioProvider(simulation_engine)
