"""Public package API exports for nessclient."""

from .client import Client
from .alarm import ArmingState, ArmingMode
from .event import BaseEvent

try:  # pragma: no cover - version is generated at build time
    from ._version import version as __version__
except ImportError:  # pragma: no cover - fallback for source builds
    __version__ = "0.0.0"

__all__ = ["Client", "ArmingState", "ArmingMode", "BaseEvent"]
