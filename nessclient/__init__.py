from .client import Client
from .alarm import ArmingState, ArmingMode
from .errors import ClientClosedError, PanelNotRespondingError
from .event import BaseEvent

try:  # pragma: no cover - version is generated at build time
    from ._version import version as __version__
except Exception:  # pragma: no cover - fallback for source builds
    __version__ = "0.0.0"

__all__ = [
    "Client",
    "ArmingState",
    "ArmingMode",
    "BaseEvent",
    "ClientClosedError",
    "PanelNotRespondingError",
]
