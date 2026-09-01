from math import exp
from threading import RLock
from app.temporal.models import *
from app.temporal.config import *

class TemporalHistoryError(ValueError): pass
class TemporalService:
    def __init__(self): self._lock=RLock(); self.reset()
    def reset(self):
        with self._lock: self._history=[]; self._ewma=None; self._cusum=0.0
    def observe(self, *, attempt_id, simulated_time, ml, baseline_revision='baseline-v1', feature_revision='bis-features-v1'):
        with self._lock:
            if self._history and simulated_time < self._history[-1].simulated_time: raise TemporalHistoryError('simulated timestamps must be monotonic')
            o=TemporalObservation(observation_id=f'{attempt_id}:temporal',measurement_attempt_id=attempt_id,simulated_time=simulated_time,reconstruction_error_mse=ml.reconstruction_error_mse,novelty_z=ml.novelty_z,model_novelty_score=ml.model_novelty_score,model_revision=ml.model_revision,baseline_revision=baseline_revision,feature_revision=feature_revision)
            dt=(simulated_time-self._history[-1].simulated_time).total_seconds() if self._history else 0.0; alpha=1-exp(-max(dt,0)/EWMA_TAU_SECONDS) if self._history else 1.0
            self._ewma=o.novelty_z if self._ewma is None else alpha*o.novelty_z+(1-alpha)*self._ewma
            self._cusum=max(0.0,self._cusum+o.novelty_z-CUSUM_REFERENCE); self._history.append(o); self._history=self._history[-MAX_HISTORY:]
            return self.assessment()
    def assessment(self):
        h=self._history; elevated=[o for o in h if o.novelty_z>=ELEVATED_Z]; span=(h[-1].simulated_time-h[0].simulated_time).total_seconds() if h else 0.0
        slope=None
        points=h[-TREND_WINDOW:]
        if len(points)>=2:
            xs=[(p.simulated_time-h[0].simulated_time).total_seconds()/86400 for p in points]; ys=[p.novelty_z for p in points]; xm=sum(xs)/len(xs); ym=sum(ys)/len(ys); den=sum((x-xm)**2 for x in xs); slope=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/den if den else None
        state=TemporalEvidenceState.INSUFFICIENT_HISTORY
        if len(h)>=2:
            if elevated and h[-1].novelty_z < ELEVATED_Z and elevated[-1] is not h[-1]: state=TemporalEvidenceState.RECOVERING_PATTERN
            elif len(elevated)>=MIN_PERSISTENCE_COUNT and span>=MIN_PERSISTENCE_SECONDS: state=TemporalEvidenceState.RISING_PERSISTENT_PATTERN if slope and slope>0 else TemporalEvidenceState.SUSTAINED_ELEVATION
            elif elevated: state=TemporalEvidenceState.TRANSIENT_ELEVATION
            else: state=TemporalEvidenceState.STABLE_PATTERN
        return TemporalAssessment(temporal_revision=TEMPORAL_REVISION,observation_count=len(h),history_start_time=h[0].simulated_time if h else None,latest_time=h[-1].simulated_time if h else None,latest_novelty_z=h[-1].novelty_z if h else None,ewma_novelty=self._ewma,cusum_value=self._cusum,cusum_engineering_threshold=CUSUM_THRESHOLD,cusum_exceeded=self._cusum>=CUSUM_THRESHOLD,elevated_observation_count=len(elevated),persistence_duration_seconds=span if len(elevated)>=MIN_PERSISTENCE_COUNT else 0.0,persistence_duration_days=(span/86400 if len(elevated)>=MIN_PERSISTENCE_COUNT else 0.0),recent_novelty_slope_per_day=slope,temporal_state=state)
    def history(self): return list(self._history)

temporal_service=TemporalService()
from app.simulation.engine import simulation_engine
simulation_engine.register_reset_hook(temporal_service.reset)
