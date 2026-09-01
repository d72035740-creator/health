from datetime import datetime
from threading import RLock
from app.domain.enums import ArmSide, SimulationLifecycle
from app.simulation.bioimpedance.models import ColeModelParameters
from app.simulation.engine import DigitalPatientEngine, simulation_engine
from app.simulation.bioimpedance.config import LEFT_ARM_PARAMETERS, RIGHT_ARM_PARAMETERS
from enum import Enum

class ScenarioType(str, Enum): BASELINE_STABLE="BASELINE_STABLE"; SYSTEMIC_BILATERAL_SHIFT="SYSTEMIC_BILATERAL_SHIFT"; TRANSIENT_UNILATERAL_SHIFT="TRANSIENT_UNILATERAL_SHIFT"; SLOW_UNILATERAL_SHIFT="SLOW_UNILATERAL_SHIFT"; RAPID_UNILATERAL_SHIFT="RAPID_UNILATERAL_SHIFT"; RECOVERY="RECOVERY"
SCENARIO_ENGINE_NAME="Aequor Longitudinal Scenario Engine"; SCENARIO_REVISION="scenario-v1"

class ScenarioSelection(dict): pass

class ScenarioState:
    def __init__(self): self.scenario_id="scenario-0"; self.scenario_type=ScenarioType.BASELINE_STABLE; self.affected_arm=None; self.start_simulated_time=None; self.elapsed_simulated_time=0.0; self.severity=0.0; self.active=False
    def as_dict(self): return {"scenario_id":self.scenario_id,"scenario_type":self.scenario_type.value,"affected_arm":self.affected_arm.value if self.affected_arm else None,"start_simulated_time":self.start_simulated_time,"elapsed_simulated_time":self.elapsed_simulated_time,"severity":self.severity,"scenario_revision":SCENARIO_REVISION,"scenario_engine_name":SCENARIO_ENGINE_NAME,"active":self.active}

class ScenarioProvider:
    def __init__(self,engine:DigitalPatientEngine): self._engine=engine; self._lock=RLock(); self._state=ScenarioState(); engine.register_reset_hook(self.reset)
    def state(self):
        with self._lock:
            self._refresh(); return self._state
    def select(self,scenario_type:ScenarioType,affected_arm:ArmSide|None=None):
        with self._lock: self._state.scenario_type=scenario_type; self._state.affected_arm=affected_arm; self._state.active=False; self._state.severity=0.0
    def start(self):
        with self._lock:
            snap=self._engine.snapshot(); self._state.start_simulated_time=snap.simulated_time; self._state.active=True; self._state.severity=0.0
    def reset(self):
        with self._lock: self._state=ScenarioState()
    def _refresh(self):
        if not self._state.active or self._state.start_simulated_time is None:return
        now=self._engine.snapshot().simulated_time; self._state.elapsed_simulated_time=max(0,(now-self._state.start_simulated_time).total_seconds()); kind=self._state.scenario_type
        if kind is ScenarioType.TRANSIENT_UNILATERAL_SHIFT: self._state.severity=min(1.0, self._state.elapsed_simulated_time/172800); self._state.severity=2*self._state.severity if self._state.severity<.5 else 2*(1-self._state.severity)
        elif kind is ScenarioType.RAPID_UNILATERAL_SHIFT:self._state.severity=min(1.0,self._state.elapsed_simulated_time/172800)
        else:self._state.severity=min(1.0,self._state.elapsed_simulated_time/(7*86400))
    def effective_parameters(self,arm:ArmSide,simulated_time:datetime,base:ColeModelParameters)->ColeModelParameters:
        with self._lock:
            self._refresh(); s=self._state.severity; kind=self._state.scenario_type; affected=self._state.affected_arm
            if kind is ScenarioType.BASELINE_STABLE or not self._state.active:return base
            applies=kind is ScenarioType.SYSTEMIC_BILATERAL_SHIFT or (affected is arm)
            if kind is ScenarioType.RECOVERY: applies=affected is arm
            if not applies:return base
            sign=1.0 if kind is not ScenarioType.RECOVERY else max(0.0,1-s)
            magnitude=s*sign
            if kind is ScenarioType.SYSTEMIC_BILATERAL_SHIFT:magnitude=.12*s
            return ColeModelParameters(r_zero_ohm=base.r_zero_ohm*(1+.18*magnitude),r_infinity_ohm=base.r_infinity_ohm*(1+.10*magnitude),tau_seconds=base.tau_seconds*(1+.45*magnitude),beta=max(.05,min(1,base.beta-.08*magnitude)))

scenario_provider=ScenarioProvider(simulation_engine)
