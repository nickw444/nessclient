from dataclasses import dataclass
from enum import Enum


@dataclass
class Zone:
    """Holds the current state of a zone within the test alarm emulator."""

    class State(Enum):
        """Represents whether a zone is sealed or unsealed."""

        SEALED = "SEALED"
        UNSEALED = "UNSEALED"

    id: int
    state: State
