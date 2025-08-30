from dataclasses import dataclass
from enum import Enum


@dataclass
class AuxOutput:
    class State(Enum):
        OFF = "OFF"
        ON = "ON"

    id: int
    state: State
