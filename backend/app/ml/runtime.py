import hashlib,json,math,time
from pathlib import Path
from app.ml.config import *
from app.ml.models import MLInferenceResult
from app.domain.enums import DataProvenance,SubsystemStatus
class MLRuntime:
    def __init__(self): self._interpreter=None; self.metadata=None; self.error=None
    def load(self):
        artifact=MODEL_DIR/f"{MODEL_REVISION}-int8.tflite"; meta=MODEL_DIR/f"{MODEL_REVISION}.metadata.json"
        if not artifact.exists() or not meta.exists(): self.error="INT8 TFLite model artifact is unavailable"; return False
        try:
            self.metadata=json.loads(meta.read_text()); digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
            if digest!=self.metadata.get("artifacts",{}).get("int8_sha256"): raise ValueError("model SHA256 mismatch")
            try:
                from tensorflow.lite import Interpreter
            except ImportError:
                try:
                    from tflite_runtime.interpreter import Interpreter
                except ImportError:
                    from ai_edge_litert.interpreter import Interpreter
            self._interpreter=Interpreter(model_path=str(artifact)); self._interpreter.allocate_tensors(); self.error=None; return True
        except Exception as exc: self.error=str(exc); self._interpreter=None; return False
    def status(self): return {"status":"READY" if self._interpreter else "ERROR","model_name":"Aequor Tiny Autoencoder","model_revision":MODEL_REVISION,"runtime":"TFLITE_INT8","ml_input_revision":ML_INPUT_REVISION,"feature_revision":FEATURE_REVISION,"loaded":self._interpreter is not None,"error":self.error,"model_size_bytes":(MODEL_DIR/f"{MODEL_REVISION}-int8.tflite").stat().st_size if (MODEL_DIR/f"{MODEL_REVISION}-int8.tflite").exists() else None}
    def infer(self,values:list[float])->MLInferenceResult:
        if self._interpreter is None: return MLInferenceResult(status=SubsystemStatus.ERROR,error=self.error or "INT8 TFLite model is unavailable")
        try:
            import numpy as np
            inp=self._interpreter.get_input_details()[0]; out=self._interpreter.get_output_details()[0]; scale,zp=inp["quantization"]; oscale,ozp=out["quantization"]
            if not scale or not oscale: raise ValueError("model tensors are not quantized")
            x=np.asarray(values,dtype=np.float32); q=np.clip(np.round(x/scale+zp),-128,127).astype(np.int8); start=time.perf_counter(); self._interpreter.set_tensor(inp["index"],q.reshape(inp["shape"])); self._interpreter.invoke(); recon=oscale*(self._interpreter.get_tensor(out["index"]).astype(np.float32)-ozp); latency=(time.perf_counter()-start)*1000; mse=float(np.mean((x-recon.reshape(-1))**2)); eps=self.metadata["calibration"]["epsilon"]; med=self.metadata["calibration"]["validation_log_error_median"]; robust=self.metadata["calibration"]["validation_log_error_scale"]; temp=self.metadata["calibration"]["mapping_temperature"]; z=float((math.log(mse+eps)-med)/robust); score=float(1/(1+math.exp(-z/temp)))
            return MLInferenceResult(status=SubsystemStatus.READY,model_name="Aequor Tiny Autoencoder",model_revision=MODEL_REVISION,ml_input_revision=ML_INPUT_REVISION,feature_revision=FEATURE_REVISION,inference_runtime="TFLITE_INT8",reconstruction_error_mse=mse,novelty_z=z,model_novelty_score=score,inference_latency_ms=latency,input_dimension=len(values),model_size_bytes=(MODEL_DIR/f"{MODEL_REVISION}-int8.tflite").stat().st_size,provenance=DataProvenance.SIMULATED)
        except Exception as exc:return MLInferenceResult(status=SubsystemStatus.ERROR,error=str(exc))
ml_runtime=MLRuntime(); ml_runtime.load()
