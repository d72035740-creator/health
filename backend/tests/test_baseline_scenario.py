from app.baseline.service import PersonalizedBaselineService, BaselineError
from app.simulation.engine import DigitalPatientEngine
from app.simulation.sensors.models import SensorWindowRequest
from app.measurement import MeasurementAttemptService
from app.scenario import ScenarioProvider, ScenarioType
from app.domain.enums import ArmSide
from app.simulation.bioimpedance.config import LEFT_ARM_PARAMETERS

def test_baseline_statistics_and_span_guards():
    baseline=PersonalizedBaselineService(); assert baseline.snapshot().state.value=="UNINITIALIZED"; baseline.start()
    # A single timestamp cannot satisfy the longitudinal calibration span.
    try: baseline.finalize(); assert False
    except BaselineError: pass

def test_scenario_time_progression_and_reset():
    engine=DigitalPatientEngine(); provider=ScenarioProvider(engine); provider.select(ScenarioType.SLOW_UNILATERAL_SHIFT,ArmSide.LEFT); provider.start(); initial=provider.state().severity; engine.step(3*86400); assert provider.state().severity>initial; left=provider.effective_parameters(ArmSide.LEFT,engine.snapshot().simulated_time,LEFT_ARM_PARAMETERS); right=provider.effective_parameters(ArmSide.RIGHT,engine.snapshot().simulated_time,LEFT_ARM_PARAMETERS); assert left.tau_seconds!=right.tau_seconds; provider.reset(); assert provider.state().scenario_type is ScenarioType.BASELINE_STABLE and provider.state().severity==0

def test_phase7_state_does_not_enter_processed_feature_contract():
    engine=DigitalPatientEngine(); provider=ScenarioProvider(engine); provider.select(ScenarioType.SYSTEMIC_BILATERAL_SHIFT); provider.start(); assert "severity" not in provider.effective_parameters(ArmSide.LEFT,engine.snapshot().simulated_time,LEFT_ARM_PARAMETERS).model_dump()
