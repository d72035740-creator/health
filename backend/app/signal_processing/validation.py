import math
from app.simulation.bioimpedance.models import BilateralBioimpedanceSweep

class ProcessingValidationError(ValueError): pass

def validate_sweep(sweep: BilateralBioimpedanceSweep, expected_frequencies: tuple[float, ...]) -> None:
    if sweep.left is None or sweep.right is None: raise ProcessingValidationError("both LEFT and RIGHT sweeps are required")
    lf=[p.frequency_hz for p in sweep.left.points]; rf=[p.frequency_hz for p in sweep.right.points]
    if tuple(lf)!=tuple(rf): raise ProcessingValidationError("left/right frequency sets do not match")
    if tuple(lf)!=expected_frequencies: raise ProcessingValidationError("sweep frequencies do not match configured frequencies")
    if sweep.left.wall_clock_time != sweep.right.wall_clock_time or sweep.left.simulated_time != sweep.right.simulated_time or sweep.provenance != sweep.left.provenance or sweep.provenance != sweep.right.provenance: raise ProcessingValidationError("bilateral sweep metadata is not synchronized")
    for point in [*sweep.left.points,*sweep.right.points]:
        values=(point.frequency_hz,point.resistance_ohm,point.reactance_ohm,point.magnitude_ohm,point.phase_deg)
        if not all(math.isfinite(v) for v in values) or point.frequency_hz<=0 or point.magnitude_ohm<=0: raise ProcessingValidationError("sweep contains non-finite or non-positive values")
        expected_mag=math.hypot(point.resistance_ohm,point.reactance_ohm); expected_phase=math.degrees(math.atan2(point.reactance_ohm,point.resistance_ohm))
        if not math.isclose(point.magnitude_ohm,expected_mag,rel_tol=.02,abs_tol=.01): raise ProcessingValidationError("magnitude is inconsistent with R/X")
        if abs(point.phase_deg-expected_phase)>1.0: raise ProcessingValidationError("phase is inconsistent with R/X")
