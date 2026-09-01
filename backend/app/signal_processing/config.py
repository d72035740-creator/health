PROCESSOR_NAME = "Aequor BIS Feature Processor"
FEATURE_REVISION = "bis-features-v1"
EXPECTED_FREQUENCIES_HZ = (5_000.0, 10_000.0, 20_000.0, 50_000.0, 100_000.0, 200_000.0)

def processing_config() -> dict[str, object]:
    return {"processor_name": PROCESSOR_NAME, "feature_revision": FEATURE_REVISION, "frequencies_hz": list(EXPECTED_FREQUENCIES_HZ), "cole_fit_enabled": True, "cole_fit_method": "bounded deterministic coordinate descent on complex R/X residuals", "feature_definitions": {"magnitude_ratio": "abs(Z_left) / abs(Z_right)", "log_magnitude_ratio": "ln(magnitude_ratio)", "normalized_magnitude_difference": "(left-right)/mean(left,right)", "spectral_slope": "OLS slope of value against log10(frequency_hz)"}}
