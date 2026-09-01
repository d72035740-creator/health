from statistics import median
from threading import RLock
from app.baseline.config import *
from app.baseline.models import *
from app.signal_processing.models import ProcessedBioimpedanceFeatures

class BaselineError(ValueError): pass
class PersonalizedBaselineService:
    def __init__(self): self._lock=RLock(); self.reset()
    def reset(self):
        with self._lock: self._state=BaselineLifecycle.UNINITIALIZED; self._observations=[]; self._names=[]
    def start(self):
        with self._lock:
            if self._state is BaselineLifecycle.READY: raise BaselineError("baseline is already READY; reset before recalibration")
            self._state=BaselineLifecycle.CALIBRATING
    def _vector(self, features:ProcessedBioimpedanceFeatures):
        if features.feature_revision!=FEATURE_REVISION: raise BaselineError("incompatible feature revision")
        vector=features.to_ml_vector(); names=list(vector["names"]); values=list(vector["values"])
        if not self._names: self._names=names
        if names!=self._names: raise BaselineError("feature ordering mismatch")
        return features.simulated_time, values
    def capture(self, features:ProcessedBioimpedanceFeatures):
        with self._lock:
            if self._state is not BaselineLifecycle.CALIBRATING: raise BaselineError("baseline is not calibrating")
            timestamp,values=self._vector(features)
            if self._observations and (timestamp-self._observations[-1][0]).total_seconds()<MINIMUM_INTERVAL_SECONDS: raise BaselineError("baseline observations are too close together")
            self._observations.append((timestamp,values))
    def finalize(self):
        with self._lock:
            span=(self._observations[-1][0]-self._observations[0][0]).total_seconds() if self._observations else 0
            if len(self._observations)<MINIMUM_OBSERVATIONS or span<MINIMUM_SPAN_SECONDS: raise BaselineError("insufficient observations or simulated span")
            self._state=BaselineLifecycle.READY
    def snapshot(self)->PersonalizedBaselineSnapshot:
        with self._lock:
            span=(self._observations[-1][0]-self._observations[0][0]).total_seconds() if self._observations else 0
            return PersonalizedBaselineSnapshot(state=self._state,baseline_engine_name=ENGINE_NAME,baseline_revision=BASELINE_REVISION,feature_revision=FEATURE_REVISION,observation_count=len(self._observations),minimum_observations=MINIMUM_OBSERVATIONS,simulated_span_seconds=span,minimum_simulated_span_seconds=MINIMUM_SPAN_SECONDS,statistics=self._statistics())
    def _statistics(self):
        if not self._observations:return []
        result=[]
        for i,name in enumerate(self._names):
            vals=sorted(row[1][i] for row in self._observations); med=median(vals); lower=vals[:len(vals)//2]; upper=vals[(len(vals)+1)//2:]; q1=median(lower) if lower else med; q3=median(upper) if upper else med; mad=median([abs(v-med) for v in vals]); iqr=q3-q1; scale=1.4826*mad or (iqr/1.349 if iqr else FEATURE_SCALE_FLOOR); result.append(BaselineFeatureStatistics(name=name,count=len(vals),median=med,mad=mad,q1=q1,q3=q3,iqr=iqr,robust_scale=max(scale,FEATURE_SCALE_FLOOR)))
        return result
    def compare(self, features:ProcessedBioimpedanceFeatures)->BaselineComparison:
        with self._lock:
            if self._state is not BaselineLifecycle.READY: raise BaselineError("baseline is not READY")
            _,values=self._vector(features); stats=self._statistics(); return BaselineComparison(feature_revision=FEATURE_REVISION,values=[BaselineComparisonValue(name=s.name,current_value=v,baseline_median=s.median,baseline_scale=s.robust_scale,signed_normalized_delta=(v-s.median)/s.robust_scale) for s,v in zip(stats,values,strict=True)])

baseline_service=PersonalizedBaselineService()
from app.simulation.engine import simulation_engine
simulation_engine.register_reset_hook(baseline_service.reset)
