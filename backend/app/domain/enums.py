from enum import Enum


class DataProvenance(str, Enum):
    SIMULATED = "SIMULATED"
    HARDWARE = "HARDWARE"


class ArmSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class SubsystemStatus(str, Enum):
    READY = "READY"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class SurveillanceState(str, Enum):
    CALIBRATING = "CALIBRATING"
    WITHIN_BASELINE = "WITHIN_BASELINE"
    OBSERVING_CHANGE = "OBSERVING_CHANGE"
    PERSISTENT_DEVIATION = "PERSISTENT_DEVIATION"
    CLINICAL_REVIEW_RECOMMENDED = "CLINICAL_REVIEW_RECOMMENDED"


class PrototypeMode(str, Enum):
    SIMULATION = "SIMULATION"


class SimulationLifecycle(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class DataLayer(str, Enum):
    RAW = "RAW"
    PROCESSED = "PROCESSED"
    INFERENCE = "INFERENCE"
    TEMPORAL = "TEMPORAL"
    DECISION = "DECISION"
