from app.domain.enums import DataProvenance
from app.simulation.bioimpedance.models import (
    AcquisitionQualification,
    BioimpedanceSourceType,
    BioimpedanceTwinConfiguration,
    ColeModelParameters,
    FrequencyConfiguration,
    InstrumentationNoiseConfiguration,
)


MODEL_NAME = "Cole Digital Twin"
MODEL_REVISION = "cole-v1"

DEFAULT_FREQUENCIES = FrequencyConfiguration(
    frequencies_hz=[5_000, 10_000, 20_000, 50_000, 100_000, 200_000]
)

# Prototype demonstration parameters only; not population-normal reference ranges.
LEFT_ARM_PARAMETERS = ColeModelParameters(
    r_zero_ohm=620.0,
    r_infinity_ohm=310.0,
    tau_seconds=30e-6,
    beta=0.76,
)

RIGHT_ARM_PARAMETERS = ColeModelParameters(
    r_zero_ohm=612.0,
    r_infinity_ohm=306.0,
    tau_seconds=32e-6,
    beta=0.75,
)

DEFAULT_NOISE = InstrumentationNoiseConfiguration(
    enabled=True,
    relative_bound=0.0015,
)


def default_configuration(
    *,
    noise: InstrumentationNoiseConfiguration = DEFAULT_NOISE,
) -> BioimpedanceTwinConfiguration:
    return BioimpedanceTwinConfiguration(
        model_name=MODEL_NAME,
        model_revision=MODEL_REVISION,
        frequencies_hz=DEFAULT_FREQUENCIES.frequencies_hz,
        provenance=DataProvenance.SIMULATED,
        source=BioimpedanceSourceType.DIGITAL_TWIN,
        qualification=AcquisitionQualification.RAW_UNQUALIFIED,
        noise=noise,
        left_parameters=LEFT_ARM_PARAMETERS,
        right_parameters=RIGHT_ARM_PARAMETERS,
    )

