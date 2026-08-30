import hashlib
import random


class SimulationRandom:
    """Owns deterministic randomness without touching Python's global RNG."""

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    @property
    def seed(self) -> int:
        return self._seed

    def reset(self) -> None:
        self._rng.seed(self._seed)

    def derive_seed(self, namespace: str) -> int:
        """Derive stable future-module seeds without consuming shared RNG state."""
        digest = hashlib.sha256(f"{self._seed}:{namespace}".encode()).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=False)

