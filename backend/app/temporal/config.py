ENGINE_NAME='Aequor Temporal Intelligence Engine'; TEMPORAL_REVISION='temporal-v1'
EWMA_TAU_SECONDS=2*86400.0; CUSUM_REFERENCE=0.5; CUSUM_THRESHOLD=3.0
ELEVATED_Z=1.0; TREND_WINDOW=5; MIN_PERSISTENCE_COUNT=3; MIN_PERSISTENCE_SECONDS=2*86400.0
MAX_HISTORY=256

def public_config():
    return {'temporal_engine_name':ENGINE_NAME,'temporal_revision':TEMPORAL_REVISION,'ewma_tau_seconds':EWMA_TAU_SECONDS,'cusum_reference':CUSUM_REFERENCE,'cusum_engineering_threshold':CUSUM_THRESHOLD,'elevated_novelty_z':ELEVATED_Z,'trend_window':TREND_WINDOW,'minimum_persistence_observations':MIN_PERSISTENCE_COUNT,'minimum_persistence_seconds':MIN_PERSISTENCE_SECONDS}
