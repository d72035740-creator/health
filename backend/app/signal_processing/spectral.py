import math
from statistics import mean
from app.domain.models import BioimpedanceSweep
from app.signal_processing.models import FrequencyFeature, SpectralFeatures

def _slope(xs:list[float], ys:list[float]) -> float:
    xm,ym=mean(xs),mean(ys); den=sum((x-xm)**2 for x in xs)
    return sum((x-xm)*(y-ym) for x,y in zip(xs,ys,strict=True))/den if den else 0.0

def bilateral_features(left:BioimpedanceSweep,right:BioimpedanceSweep)->list[FrequencyFeature]:
    result=[]
    for lp,rp in zip(left.points,right.points,strict=True):
        ratio=lp.magnitude_ohm/rp.magnitude_ohm; denom=(lp.magnitude_ohm+rp.magnitude_ohm)/2
        result.append(FrequencyFeature(frequency_hz=lp.frequency_hz,magnitude_ratio=ratio,log_magnitude_ratio=math.log(ratio),abs_log_magnitude_ratio=abs(math.log(ratio)),resistance_ratio=lp.resistance_ohm/rp.resistance_ohm,reactance_difference_ohm=lp.reactance_ohm-rp.reactance_ohm,phase_difference_deg=lp.phase_deg-rp.phase_deg,abs_phase_difference_deg=abs(lp.phase_deg-rp.phase_deg),normalized_magnitude_difference=(lp.magnitude_ohm-rp.magnitude_ohm)/denom if denom else 0.0))
    return result

def arm_spectral(sweep:BioimpedanceSweep)->SpectralFeatures:
    points=sweep.points; xs=[math.log10(p.frequency_hz) for p in points]; mags=[p.magnitude_ohm for p in points]; resist=[p.resistance_ohm for p in points]; phases=[p.phase_deg for p in points]
    return SpectralFeatures(low_high_magnitude_ratio=mags[0]/mags[-1],low_high_resistance_ratio=resist[0]/resist[-1],magnitude_log_frequency_slope_ohm_per_log10_hz=_slope(xs,mags),resistance_log_frequency_slope_ohm_per_log10_hz=_slope(xs,resist),phase_range_deg=max(phases)-min(phases),reactance_peak_ohm=max((abs(p.reactance_ohm) for p in points),default=None))
