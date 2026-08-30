from enum import Enum
from typing import Annotated, Self

from pydantic import AwareDatetime, Field, model_validator

from app.domain.enums import ArmSide, DataProvenance
from app.domain.models import ContractModel
from app.simulation.bioimpedance.models import AcquisitionQualification


class MotionCondition(str, Enum):
    STABLE_REST = "STABLE_REST"
    ACTIVE_MOTION = "ACTIVE_MOTION"
    POSTURE_TRANSITION = "POSTURE_TRANSITION"


class ContactCondition(str, Enum):
    NOMINAL_CONTACT = "NOMINAL_CONTACT"
    UNSTABLE_CONTACT = "UNSTABLE_CONTACT"
    POOR_CONTACT = "POOR_CONTACT"


class VirtualSensorSourceType(str, Enum):
    DIGITAL_TWIN = "DIGITAL_TWIN"


class SensorWindowRequest(ContractModel):
    motion_condition: MotionCondition = MotionCondition.STABLE_REST
    contact_condition: ContactCondition = ContactCondition.NOMINAL_CONTACT
    temperature_offset_c: Annotated[float, Field(ge=-10, le=10)] = 0.0


class IMUSample(ContractModel):
    relative_time_seconds: Annotated[float, Field(ge=0)]
    acceleration_x_m_s2: float
    acceleration_y_m_s2: float
    acceleration_z_m_s2: float
    angular_velocity_x_rad_s: float
    angular_velocity_y_rad_s: float
    angular_velocity_z_rad_s: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float


class TemperatureSample(ContractModel):
    relative_time_seconds: Annotated[float, Field(ge=0)]
    temperature_c: float


class ContactSample(ContractModel):
    relative_time_seconds: Annotated[float, Field(ge=0)]
    contact_impedance_ohm: Annotated[float, Field(gt=0)]


class BandSensorWindow(ContractModel):
    arm_side: ArmSide
    imu_sample_rate_hz: Annotated[float, Field(gt=0)]
    temperature_sample_rate_hz: Annotated[float, Field(gt=0)]
    contact_sample_rate_hz: Annotated[float, Field(gt=0)]
    imu_samples: list[IMUSample] = Field(min_length=1)
    temperature_samples: list[TemperatureSample] = Field(min_length=1)
    contact_samples: list[ContactSample] = Field(min_length=1)


class WearableSensorWindow(ContractModel):
    window_id: str = Field(min_length=1)
    window_index: Annotated[int, Field(ge=1)]
    simulation_id: str = Field(min_length=1)
    anchor_simulated_time: AwareDatetime
    anchor_wall_clock_time: AwareDatetime
    duration_seconds: Annotated[float, Field(gt=0)]
    provenance: DataProvenance
    source: VirtualSensorSourceType
    qualification: AcquisitionQualification
    motion_condition: MotionCondition
    contact_condition: ContactCondition
    temperature_offset_c: float
    model_revision: str
    left: BandSensorWindow
    right: BandSensorWindow

    @model_validator(mode="after")
    def validate_bilateral_window(self) -> Self:
        if self.left.arm_side is not ArmSide.LEFT or self.right.arm_side is not ArmSide.RIGHT:
            raise ValueError("bilateral sensor window arm labels are invalid")
        return self


class VirtualSensorConfiguration(ContractModel):
    model_name: str
    model_revision: str
    duration_seconds: Annotated[float, Field(gt=0)]
    imu_sample_rate_hz: Annotated[float, Field(gt=0)]
    temperature_sample_rate_hz: Annotated[float, Field(gt=0)]
    contact_sample_rate_hz: Annotated[float, Field(gt=0)]
    supported_motion_conditions: list[MotionCondition]
    supported_contact_conditions: list[ContactCondition]
    provenance: DataProvenance
    source: VirtualSensorSourceType
    qualification: AcquisitionQualification
