from dataclasses import dataclass
from enum import Enum


@dataclass
class Output:
    class State(Enum):
        OFF = "OFF"
        ON = "ON"

    id: int
    state: State
