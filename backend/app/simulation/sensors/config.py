from app.domain.enums import DataProvenance
from app.simulation.bioimpedance.models import AcquisitionQualification
from app.simulation.sensors.models import ContactCondition, MotionCondition, VirtualSensorConfiguration, VirtualSensorSourceType

MODEL_NAME = "Virtual Wearable Sensor Layer"
MODEL_REVISION = "wearable-sensors-v1"
WINDOW_DURATION_SECONDS = 3.0
IMU_SAMPLE_RATE_HZ = 50.0
TEMPERATURE_SAMPLE_RATE_HZ = 4.0
CONTACT_SAMPLE_RATE_HZ = 12.0
GRAVITY_M_S2 = 9.80665


def default_configuration() -> VirtualSensorConfiguration:
    return VirtualSensorConfiguration(
        model_name=MODEL_NAME, model_revision=MODEL_REVISION,
        duration_seconds=WINDOW_DURATION_SECONDS, imu_sample_rate_hz=IMU_SAMPLE_RATE_HZ,
        temperature_sample_rate_hz=TEMPERATURE_SAMPLE_RATE_HZ, contact_sample_rate_hz=CONTACT_SAMPLE_RATE_HZ,
        supported_motion_conditions=list(MotionCondition), supported_contact_conditions=list(ContactCondition),
        provenance=DataProvenance.SIMULATED, source=VirtualSensorSourceType.DIGITAL_TWIN,
        qualification=AcquisitionQualification.RAW_UNQUALIFIED,
    )
