"""Type definitions for the Sprites SDK."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SpriteConfig:
    """Configuration for creating a sprite."""

    ram_mb: Optional[int] = None
    cpus: Optional[int] = None
    region: Optional[str] = None
    storage_gb: Optional[int] = None


@dataclass
class Checkpoint:
    """Represents a sprite checkpoint."""

    id: str
    create_time: datetime
    comment: Optional[str] = None
    history: Optional[list[str]] = None


@dataclass
class StreamMessage:
    """A message from a streaming operation (checkpoint create/restore)."""

    type: str  # "info", "stdout", "stderr", "error"
    data: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Session:
    """Represents an active session on a sprite."""

    id: str
    command: str
    workdir: str
    created: datetime
    bytes_per_second: int = 0
    is_active: bool = False
    last_activity: Optional[datetime] = None
    tty: bool = False


@dataclass
class PolicyRule:
    """A network policy rule."""

    domain: Optional[str] = None
    action: Optional[str] = None  # "allow" or "deny"
    include: Optional[str] = None


@dataclass
class NetworkPolicy:
    """Network policy for a sprite."""

    rules: list[PolicyRule] = field(default_factory=list)


@dataclass
class SpriteInfo:
    """Information about a sprite from the API."""

    name: str
    id: Optional[str] = None
    status: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    region: Optional[str] = None
    ram_mb: Optional[int] = None
    cpus: Optional[int] = None
    storage_gb: Optional[int] = None


@dataclass
class URLSettings:
    """URL settings for a sprite."""

    auth: str = "sprite"  # "sprite", "public", or "none"


@dataclass
class Service:
    """Service definition."""

    name: str
    cmd: str
    args: list[str] = field(default_factory=list)
    needs: list[str] = field(default_factory=list)
    http_port: Optional[int] = None


@dataclass
class ServiceState:
    """Current state of a service."""

    name: str
    status: str  # "running", "stopped", "starting", "stopping", "failed"
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    next_restart_at: Optional[datetime] = None
    error: Optional[str] = None
    restart_count: int = 0


@dataclass
class ServiceWithState:
    """Service with its current state."""

    service: Service
    state: Optional[ServiceState] = None


@dataclass
class ServiceLogEvent:
    """Event from a service operation stream."""

    type: str  # "stdout", "stderr", "exit", "error", "complete", "started", "stopping", "stopped"
    data: Optional[str] = None
    exit_code: Optional[int] = None
    timestamp: Optional[int] = None
    log_files: Optional[dict[str, str]] = None
