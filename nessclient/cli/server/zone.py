"""Zone model used by the simulator server."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class Zone:
    """Represents a simulator zone and its state."""

    class State(Enum):
        """Zone sealed/unsealed state."""
        SEALED = "SEALED"
        UNSEALED = "UNSEALED"

    id: int
    state: State
