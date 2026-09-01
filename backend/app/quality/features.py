import math
from statistics import mean, median, pstdev
from app.simulation.sensors.models import BandSensorWindow, WearableSensorWindow

def _stats(values: list[float]) -> tuple[float, float, float]:
    if len(values) < 2: raise ValueError("insufficient samples")
    if not all(math.isfinite(v) for v in values): raise FloatingPointError("non-finite sensor data")
    return mean(values), pstdev(values), max(values) - min(values)

def extract_band_features(band: BandSensorWindow) -> dict[str, float]:
    if not band.imu_samples or not band.temperature_samples or not band.contact_samples: raise ValueError("missing modality")
    acc = [math.sqrt(s.acceleration_x_m_s2**2+s.acceleration_y_m_s2**2+s.acceleration_z_m_s2**2) for s in band.imu_samples]
    gyro = [math.sqrt(s.angular_velocity_x_rad_s**2+s.angular_velocity_y_rad_s**2+s.angular_velocity_z_rad_s**2) for s in band.imu_samples]
    temp = [s.temperature_c for s in band.temperature_samples]; contact = [s.contact_impedance_ohm for s in band.contact_samples]
    am, asd, ar = _stats(acc); gm, gsd, gr = _stats(gyro); tm, tsd, tr = _stats(temp); cm, csd, cr = _stats(contact)
    if any(not math.isfinite(v) for v in [*acc,*gyro,*temp,*contact]): raise FloatingPointError("non-finite sensor data")
    first, last = band.imu_samples[0], band.imu_samples[-1]
    return {"acceleration_mean_m_s2":am, "acceleration_sd_m_s2":asd, "acceleration_range_m_s2":ar, "gyro_rms_rad_s":math.sqrt(mean(v*v for v in gyro)), "gyro_sd_rad_s":gsd, "gyro_max_rad_s":max(gyro), "roll_drift_deg":abs(last.roll_deg-first.roll_deg), "pitch_drift_deg":abs(last.pitch_deg-first.pitch_deg), "yaw_drift_deg":abs(last.yaw_deg-first.yaw_deg), "contact_mean_ohm":cm, "contact_median_ohm":median(contact), "contact_sd_ohm":csd, "contact_cv":csd/abs(cm) if cm else math.inf, "contact_range_ohm":cr, "temperature_mean_c":tm, "temperature_sd_c":tsd, "temperature_range_c":tr, "temperature_drift_c":abs(temp[-1]-temp[0])}

def extract_features(window: WearableSensorWindow) -> dict[str, dict[str, float]]:
    return {"LEFT": extract_band_features(window.left), "RIGHT": extract_band_features(window.right)}
