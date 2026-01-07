"""Sprites SDK - Python client for remote command execution on Sprites."""

from sprites.client import SpritesClient
from sprites.exceptions import APIError, ExitError, TimeoutError
from sprites.exec import Cmd, CompletedProcess, run
from sprites.services import ServiceStream
from sprites.session import KillStream
from sprites.sprite import Sprite
from sprites.types import (
    Checkpoint,
    NetworkPolicy,
    PolicyRule,
    Service,
    ServiceLogEvent,
    ServiceState,
    ServiceWithState,
    Session,
    SpriteConfig,
    SpriteInfo,
    StreamMessage,
    URLSettings,
)

__all__ = [
    # Client
    "SpritesClient",
    "Sprite",
    # Command execution
    "Cmd",
    "CompletedProcess",
    "run",
    # Exceptions
    "ExitError",
    "APIError",
    "TimeoutError",
    # Configuration
    "SpriteConfig",
    "SpriteInfo",
    "URLSettings",
    # Checkpoints
    "Checkpoint",
    "StreamMessage",
    # Network policy
    "NetworkPolicy",
    "PolicyRule",
    # Sessions
    "Session",
    "KillStream",
    # Services
    "Service",
    "ServiceState",
    "ServiceWithState",
    "ServiceLogEvent",
    "ServiceStream",
]

__version__ = "0.1.0"
