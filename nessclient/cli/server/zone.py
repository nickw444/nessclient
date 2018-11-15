from dataclasses import dataclass
from enum import Enum


@dataclass
class Zone:
    class State(Enum):
        SEALED = 'SEALED'
        UNSEALED = 'UNSEALED'

    id: int
    state: State
