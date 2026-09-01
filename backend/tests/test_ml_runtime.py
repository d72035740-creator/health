import hashlib
from pathlib import Path
from app.ml.runtime import MLRuntime
from app.ml.config import MODEL_DIR, MODEL_REVISION

def test_int8_runtime_loads_and_returns_finite_score():
    runtime=MLRuntime(); assert runtime.load(); result=runtime.infer([0.0]*34); assert result.status.value=="READY"; assert 0<=result.model_novelty_score<=1; assert result.input_dimension==34

def test_missing_artifact_is_explicitly_unavailable():
    runtime=MLRuntime(); runtime.metadata={}; original=MODEL_DIR
    import app.ml.runtime as module
    module.MODEL_DIR=Path("__missing_model_directory__")
    try: assert runtime.load() is False; assert runtime.status()["status"]=="ERROR"; assert runtime.error
    finally: module.MODEL_DIR=original

def test_artifact_hash_matches_metadata():
    artifact=MODEL_DIR/f"{MODEL_REVISION}-int8.tflite"; metadata=(MODEL_DIR/f"{MODEL_REVISION}.metadata.json").read_text(); assert hashlib.sha256(artifact.read_bytes()).hexdigest() in metadata
