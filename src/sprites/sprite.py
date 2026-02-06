"""
Sprite class representing a sprite instance
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from datetime import datetime
import httpx

from .types import (
    SpriteConfig,
    URLSettings,
    Checkpoint,
    Session,
    NetworkPolicy,
    PolicyRule,
    ServiceWithState,
    ServiceRequest,
    ServiceState,
)
from .exceptions import (
    SpriteError,
    NetworkError,
    NotFoundError,
)

if TYPE_CHECKING:
    from .client import SpritesClient
    from .filesystem import SpriteFilesystem


class Sprite:
    """Represents a sprite instance."""

    def __init__(self, name: str, client: "SpritesClient"):
        """
        Initialize a Sprite instance.

        Args:
            name: Sprite name
            client: SpritesClient instance
        """
        self.name = name
        self.client = client

        # Additional properties from API
        self.id: Optional[str] = None
        self.organization_name: Optional[str] = None
        self.status: Optional[str] = None
        self.config: Optional[SpriteConfig] = None
        self.environment: Optional[Dict[str, str]] = None
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self.bucket_name: Optional[str] = None
        self.primary_region: Optional[str] = None
        self.url: Optional[str] = None
        self.url_settings: Optional[URLSettings] = None

    def _update_from_info(self, info: Dict[str, Any]) -> None:
        """Update sprite properties from API response."""
        self.id = info.get("id")
        self.organization_name = info.get("organization")
        self.status = info.get("status")
        self.url = info.get("url")
        self.primary_region = info.get("primary_region")
        self.bucket_name = info.get("bucket_name")

        if "created_at" in info and info["created_at"]:
            try:
                self.created_at = datetime.fromisoformat(
                    info["created_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        if "updated_at" in info and info["updated_at"]:
            try:
                self.updated_at = datetime.fromisoformat(
                    info["updated_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

    def _headers(self) -> Dict[str, str]:
        """Get default headers with authorization."""
        return {
            "Authorization": f"Bearer {self.client.token}",
            "Content-Type": "application/json",
        }

    def _base_url(self) -> str:
        """Get sprite-specific base URL."""
        return f"{self.client.base_url}/v1/sprites/{self.name}"

    # ========== Filesystem API ==========

    def filesystem(self, working_dir: str = "/") -> "SpriteFilesystem":
        """
        Get a filesystem interface for the sprite.

        Args:
            working_dir: Working directory to use as root (default: "/")

        Returns:
            SpriteFilesystem instance that supports pathlib.Path-like operations
        """
        from .filesystem import SpriteFilesystem
        return SpriteFilesystem(self, working_dir)

    # ========== Lifecycle API ==========

    def delete(self) -> None:
        """Delete this sprite."""
        self.client.delete_sprite(self.name)

    def destroy(self) -> None:
        """Alias for delete()."""
        self.delete()

    def upgrade(self) -> None:
        """Upgrade this sprite to the latest version."""
        self.client.upgrade_sprite(self.name)

    def update_url_settings(self, settings: URLSettings) -> None:
        """
        Update URL authentication settings.

        Args:
            settings: URL settings with auth: "public" for no auth, "sprite" for authenticated
        """
        self.client.update_url_settings(self.name, settings)

    # ========== Sessions API ==========

    def list_sessions(self) -> List[Session]:
        """
        List active sessions.

        Returns:
            List of Session objects
        """
        try:
            response = self.client._client.get(
                f"{self._base_url()}/exec",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error listing sessions: {e}")

        if not response.is_success:
            raise SpriteError(
                f"Failed to list sessions (status {response.status_code}): {response.text}"
            )

        result = response.json()
        sessions: List[Session] = []

        for s in result.get("sessions", []):
            last_activity = None
            if s.get("last_activity"):
                try:
                    last_activity = datetime.fromisoformat(
                        s["last_activity"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            created = datetime.now()
            if s.get("created"):
                try:
                    created = datetime.fromisoformat(
                        s["created"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            sessions.append(Session(
                id=s.get("id", ""),
                command=s.get("command", ""),
                workdir=s.get("workdir", ""),
                created=created,
                bytes_per_second=s.get("bytes_per_second", 0),
                is_active=s.get("is_active", False),
                tty=s.get("tty", False),
                last_activity=last_activity,
            ))

        return sessions

    # ========== Checkpoint API ==========

    def list_checkpoints(self, history_filter: Optional[str] = None) -> List[Checkpoint]:
        """
        List checkpoints.

        Args:
            history_filter: Optional filter for checkpoint history

        Returns:
            List of Checkpoint objects
        """
        url = f"{self._base_url()}/checkpoints"
        params = {}
        if history_filter:
            params["history"] = history_filter

        try:
            response = self.client._client.get(
                url,
                headers=self._headers(),
                params=params if params else None,
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error listing checkpoints: {e}")

        if not response.is_success:
            raise SpriteError(
                f"Failed to list checkpoints (status {response.status_code}): {response.text}"
            )

        raw = response.json()
        checkpoints: List[Checkpoint] = []

        for cp in raw:
            create_time = datetime.now()
            if cp.get("create_time"):
                try:
                    create_time = datetime.fromisoformat(
                        cp["create_time"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            checkpoints.append(Checkpoint(
                id=cp.get("id", ""),
                create_time=create_time,
                comment=cp.get("comment"),
                history=cp.get("history"),
            ))

        return checkpoints

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        """
        Get checkpoint details.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint object
        """
        try:
            response = self.client._client.get(
                f"{self._base_url()}/checkpoints/{checkpoint_id}",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error getting checkpoint: {e}")

        if response.status_code == 404:
            raise NotFoundError(f"Checkpoint not found: {checkpoint_id}")

        if not response.is_success:
            raise SpriteError(
                f"Failed to get checkpoint (status {response.status_code}): {response.text}"
            )

        cp = response.json()
        create_time = datetime.now()
        if cp.get("create_time"):
            try:
                create_time = datetime.fromisoformat(
                    cp["create_time"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return Checkpoint(
            id=cp.get("id", ""),
            create_time=create_time,
            comment=cp.get("comment"),
            history=cp.get("history"),
        )

    def create_checkpoint(self, comment: str = ""):
        """
        Create a new checkpoint.

        Args:
            comment: Optional comment for the checkpoint

        Returns:
            Iterator of checkpoint creation messages
        """
        from .checkpoint import create_checkpoint
        return create_checkpoint(self, comment)

    def restore_checkpoint(self, checkpoint_id: str):
        """
        Restore a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to restore

        Returns:
            Iterator of restore messages
        """
        from .checkpoint import restore_checkpoint
        return restore_checkpoint(self, checkpoint_id)

    # ========== Command Execution API ==========

    def command(
        self,
        *args: str,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        Create a command to run on this sprite.

        Args:
            *args: Command and arguments
            env: Environment variables
            cwd: Working directory
            timeout: Command timeout in seconds

        Returns:
            Cmd object for executing the command
        """
        from .exec import Cmd
        return Cmd(
            sprite=self,
            args=list(args),
            env=env,
            cwd=cwd,
            timeout=timeout,
        )

    def attach_session(
        self,
        session_id: str,
        timeout: Optional[float] = None,
    ):
        """
        Attach to an existing session.

        Args:
            session_id: Session ID to attach to
            timeout: Command timeout in seconds

        Returns:
            Cmd object for the attached session
        """
        from .exec import Cmd
        return Cmd(
            sprite=self,
            args=[],
            session_id=session_id,
            timeout=timeout,
        )

    # ========== Services API ==========

    def list_services(self) -> List[ServiceWithState]:
        """
        List all services on this sprite.

        Returns:
            List of ServiceWithState objects
        """
        try:
            response = self.client._client.get(
                f"{self._base_url()}/services",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error listing services: {e}")

        if not response.is_success:
            raise SpriteError(
                f"Failed to list services (status {response.status_code}): {response.text}"
            )

        data = response.json()
        services: List[ServiceWithState] = []

        for s in data.get("services", []):
            state = None
            if s.get("state"):
                state = ServiceState(
                    name=s["state"].get("name", ""),
                    status=s["state"].get("status", "stopped"),
                    pid=s["state"].get("pid"),
                    started_at=s["state"].get("started_at"),
                    error=s["state"].get("error"),
                    restart_count=s["state"].get("restart_count", 0),
                    next_restart_at=s["state"].get("next_restart_at"),
                )

            services.append(ServiceWithState(
                name=s.get("name", ""),
                cmd=s.get("cmd", ""),
                args=s.get("args", []),
                needs=s.get("needs", []),
                http_port=s.get("http_port"),
                state=state,
            ))

        return services

    def get_service(self, service_name: str) -> ServiceWithState:
        """
        Get a specific service.

        Args:
            service_name: Service name

        Returns:
            ServiceWithState object
        """
        try:
            response = self.client._client.get(
                f"{self._base_url()}/services/{service_name}",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error getting service: {e}")

        if response.status_code == 404:
            raise NotFoundError(f"Service not found: {service_name}")

        if not response.is_success:
            raise SpriteError(
                f"Failed to get service (status {response.status_code}): {response.text}"
            )

        s = response.json()
        state = None
        if s.get("state"):
            state = ServiceState(
                name=s["state"].get("name", ""),
                status=s["state"].get("status", "stopped"),
                pid=s["state"].get("pid"),
                started_at=s["state"].get("started_at"),
                error=s["state"].get("error"),
                restart_count=s["state"].get("restart_count", 0),
                next_restart_at=s["state"].get("next_restart_at"),
            )

        return ServiceWithState(
            name=s.get("name", ""),
            cmd=s.get("cmd", ""),
            args=s.get("args", []),
            needs=s.get("needs", []),
            http_port=s.get("http_port"),
            state=state,
        )

    def delete_service(self, service_name: str) -> None:
        """
        Delete a service.

        Args:
            service_name: Service name
        """
        try:
            response = self.client._client.delete(
                f"{self._base_url()}/services/{service_name}",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error deleting service: {e}")

        if response.status_code != 204 and not response.is_success:
            raise SpriteError(
                f"Failed to delete service (status {response.status_code}): {response.text}"
            )

    # ========== Policy API ==========

    def get_network_policy(self) -> NetworkPolicy:
        """
        Get the current network policy.

        Returns:
            NetworkPolicy object
        """
        try:
            response = self.client._client.get(
                f"{self._base_url()}/policy/network",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error getting network policy: {e}")

        if not response.is_success:
            raise SpriteError(
                f"Failed to get network policy (status {response.status_code}): {response.text}"
            )

        data = response.json()
        rules: List[PolicyRule] = []

        for r in data.get("rules", []):
            rules.append(PolicyRule(
                domain=r.get("domain"),
                action=r.get("action"),
                include=r.get("include"),
            ))

        return NetworkPolicy(rules=rules)

    def update_network_policy(self, policy: NetworkPolicy) -> None:
        """
        Update the network policy.

        Args:
            policy: NetworkPolicy object
        """
        rules = []
        for r in policy.rules:
            rule: Dict[str, Any] = {}
            if r.domain:
                rule["domain"] = r.domain
            if r.action:
                rule["action"] = r.action
            if r.include:
                rule["include"] = r.include
            rules.append(rule)

        try:
            response = self.client._client.post(
                f"{self._base_url()}/policy/network",
                headers=self._headers(),
                json={"rules": rules},
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error updating network policy: {e}")

        if not response.is_success:
            raise SpriteError(
                f"Failed to update network policy (status {response.status_code}): {response.text}"
            )
