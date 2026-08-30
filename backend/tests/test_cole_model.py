import math
import random

import pytest
from pydantic import ValidationError

from app.simulation.bioimpedance.cole import ColeImpedanceModel
from app.simulation.bioimpedance.config import (
    DEFAULT_FREQUENCIES,
    LEFT_ARM_PARAMETERS,
)
from app.simulation.bioimpedance.models import ColeModelParameters, FrequencyConfiguration


@pytest.mark.parametrize(
    "values",
    [
        {"r_zero_ohm": 300, "r_infinity_ohm": 300, "tau_seconds": 1e-5, "beta": 0.8},
        {"r_zero_ohm": 200, "r_infinity_ohm": 300, "tau_seconds": 1e-5, "beta": 0.8},
        {"r_zero_ohm": 600, "r_infinity_ohm": 0, "tau_seconds": 1e-5, "beta": 0.8},
        {"r_zero_ohm": 600, "r_infinity_ohm": 300, "tau_seconds": 0, "beta": 0.8},
        {"r_zero_ohm": 600, "r_infinity_ohm": 300, "tau_seconds": 1e-5, "beta": 0},
        {"r_zero_ohm": 600, "r_infinity_ohm": 300, "tau_seconds": 1e-5, "beta": 1.1},
    ],
)
def test_cole_parameter_validation(values: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        ColeModelParameters(**values)


@pytest.mark.parametrize(
    "frequencies",
    [[0, 1_000], [5_000, 5_000], [10_000, 5_000]],
)
def test_frequency_configuration_requires_positive_ordered_unique_values(
    frequencies: list[float],
) -> None:
    with pytest.raises(ValidationError):
        FrequencyConfiguration(frequencies_hz=frequencies)


def test_ideal_cole_sweep_is_coherent_finite_and_deterministic() -> None:
    model = ColeImpedanceModel(LEFT_ARM_PARAMETERS)
    frequencies = DEFAULT_FREQUENCIES.frequencies_hz
    first = model.sweep(frequencies)

    random.seed(999)
    _ = [random.random() for _ in range(50)]
    second = model.sweep(frequencies)

    assert first == second
    assert [point.frequency_hz for point in first] == frequencies
    for point in first:
        resistance = point.impedance_ohm.real
        reactance = point.impedance_ohm.imag
        magnitude = abs(point.impedance_ohm)
        phase = math.degrees(math.atan2(reactance, resistance))
        assert magnitude == pytest.approx(math.sqrt(resistance**2 + reactance**2))
        assert phase == pytest.approx(math.degrees(math.atan2(reactance, resistance)))
        assert reactance < 0
        assert magnitude > 0
        assert math.isfinite(resistance)
        assert math.isfinite(reactance)
        assert math.isfinite(magnitude)
        assert math.isfinite(phase)

    resistances = [point.impedance_ohm.real for point in first]
    magnitudes = [abs(point.impedance_ohm) for point in first]
    assert resistances[0] > resistances[-1]
    assert magnitudes[0] > magnitudes[-1]


def test_ideal_model_rejects_non_positive_frequency() -> None:
    with pytest.raises(ValueError):
        ColeImpedanceModel(LEFT_ARM_PARAMETERS).impedance_at(0)

