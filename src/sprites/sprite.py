"""Sprite class representing a remote sprite instance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, BinaryIO

from sprites.exec import Cmd, CompletedProcess, run
from sprites.types import SpriteInfo

if TYPE_CHECKING:
    from sprites.checkpoint import CheckpointStream, RestoreStream
    from sprites.client import SpritesClient
    from sprites.services import ServiceStream
    from sprites.session import KillStream
    from sprites.types import Checkpoint, NetworkPolicy, ServiceWithState, Session


@dataclass
class Sprite:
    """Represents a sprite instance."""

    name: str
    client: SpritesClient
    info: SpriteInfo | None = None

    def command(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        tty: bool = False,
        tty_rows: int = 24,
        tty_cols: int = 80,
        timeout: float | None = None,
    ) -> Cmd:
        """Create a command to run on this sprite (Go SDK style).

        Args:
            *args: Command and arguments (first arg is the command name).
            env: Environment variables to set.
            cwd: Working directory for the command.
            stdin: File-like object to read stdin from.
            stdout: File-like object to write stdout to.
            stderr: File-like object to write stderr to.
            tty: Enable TTY/pseudo-terminal mode.
            tty_rows: Terminal height (rows).
            tty_cols: Terminal width (columns).
            timeout: Command timeout in seconds.

        Returns:
            A Cmd object that can be used to execute the command.
        """
        return Cmd(
            sprite=self,
            args=list(args),
            env=env,
            cwd=cwd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            tty=tty,
            tty_rows=tty_rows,
            tty_cols=tty_cols,
            timeout=timeout,
        )

    def run(
        self,
        *args: str,
        capture_output: bool = False,
        timeout: float | None = None,
        check: bool = False,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        tty: bool = False,
        tty_rows: int = 24,
        tty_cols: int = 80,
    ) -> CompletedProcess:
        """Run a command and wait for completion (subprocess.run style).

        Args:
            *args: Command and arguments.
            capture_output: Capture stdout and stderr.
            timeout: Timeout in seconds.
            check: Raise ExitError if command returns non-zero.
            env: Environment variables.
            cwd: Working directory.
            tty: Enable TTY mode.
            tty_rows: Terminal rows.
            tty_cols: Terminal columns.

        Returns:
            CompletedProcess with results.
        """
        return run(
            self,
            *args,
            capture_output=capture_output,
            timeout=timeout,
            check=check,
            env=env,
            cwd=cwd,
            tty=tty,
            tty_rows=tty_rows,
            tty_cols=tty_cols,
        )

    def attach_session(
        self,
        session_id: str,
        *,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        timeout: float | None = None,
    ) -> Cmd:
        """Attach to an existing session.

        Args:
            session_id: The ID of the session to attach to.
            stdin: File-like object to read stdin from.
            stdout: File-like object to write stdout to.
            stderr: File-like object to write stderr to.
            timeout: Command timeout in seconds.

        Returns:
            A Cmd object for the attached session.
        """
        return Cmd(
            sprite=self,
            args=[],
            session_id=session_id,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
        )

    def delete(self) -> None:
        """Delete this sprite."""
        self.client.delete_sprite(self.name)

    def destroy(self) -> None:
        """Destroy this sprite (alias for delete)."""
        self.delete()

    # Checkpoint operations

    def list_checkpoints(self, history_filter: str = "") -> list[Checkpoint]:
        """List all checkpoints for this sprite.

        Args:
            history_filter: Optional filter for checkpoint history.

        Returns:
            List of checkpoint objects.
        """
        from sprites.checkpoint import list_checkpoints

        return list_checkpoints(self, history_filter)

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        """Get a specific checkpoint.

        Args:
            checkpoint_id: The ID of the checkpoint.

        Returns:
            The checkpoint object.
        """
        from sprites.checkpoint import get_checkpoint

        return get_checkpoint(self, checkpoint_id)

    def create_checkpoint(self, comment: str = "") -> CheckpointStream:
        """Create a new checkpoint.

        Args:
            comment: Optional comment for the checkpoint.

        Returns:
            A stream of checkpoint creation messages.
        """
        from sprites.checkpoint import create_checkpoint

        return create_checkpoint(self, comment)

    def restore_checkpoint(self, checkpoint_id: str) -> RestoreStream:
        """Restore a checkpoint.

        Args:
            checkpoint_id: The ID of the checkpoint to restore.

        Returns:
            A stream of restore messages.
        """
        from sprites.checkpoint import restore_checkpoint

        return restore_checkpoint(self, checkpoint_id)

    # Network policy operations

    def get_network_policy(self) -> NetworkPolicy:
        """Get the current network policy.

        Returns:
            The network policy for this sprite.
        """
        from sprites.policy import get_network_policy

        return get_network_policy(self)

    def update_network_policy(self, policy: NetworkPolicy) -> None:
        """Update the network policy.

        Args:
            policy: The new network policy to set.
        """
        from sprites.policy import update_network_policy

        update_network_policy(self, policy)

    # Session operations

    def list_sessions(self) -> list[Session]:
        """List active sessions for this sprite.

        Returns:
            List of active sessions.
        """
        from sprites.session import list_sessions

        return list_sessions(self)

    def kill_session(
        self,
        session_id: str,
        signal: str = "SIGTERM",
        timeout: int = 10,
    ) -> KillStream:
        """Kill a session.

        Args:
            session_id: The ID of the session to kill.
            signal: The signal to send (default: SIGTERM).
            timeout: Timeout in seconds before force kill (default: 10).

        Returns:
            A stream of kill progress messages.
        """
        from sprites.session import kill_session

        return kill_session(self, session_id, signal, timeout)

    # Service operations

    def list_services(self) -> list[ServiceWithState]:
        """List all services for this sprite.

        Returns:
            List of services with their state.
        """
        from sprites.services import list_services

        return list_services(self)

    def get_service(self, name: str) -> ServiceWithState:
        """Get a specific service.

        Args:
            name: The name of the service.

        Returns:
            The service with its state.
        """
        from sprites.services import get_service

        return get_service(self, name)

    def create_service(
        self,
        name: str,
        cmd: str,
        args: list[str] | None = None,
        needs: list[str] | None = None,
        http_port: int | None = None,
        duration: float | None = None,
    ) -> ServiceStream:
        """Create or update a service.

        Args:
            name: The name of the service.
            cmd: The command to run.
            args: Command arguments.
            needs: Services this service depends on.
            http_port: HTTP port the service listens on.
            duration: Monitoring duration in seconds.

        Returns:
            A stream of service log events.
        """
        from sprites.services import create_service

        return create_service(self, name, cmd, args, needs, http_port, duration)

    def delete_service(self, name: str) -> None:
        """Delete a service.

        Args:
            name: The name of the service.
        """
        from sprites.services import delete_service

        delete_service(self, name)

    def start_service(
        self,
        name: str,
        duration: float | None = None,
    ) -> ServiceStream:
        """Start a service.

        Args:
            name: The name of the service.
            duration: Monitoring duration in seconds.

        Returns:
            A stream of service log events.
        """
        from sprites.services import start_service

        return start_service(self, name, duration)

    def stop_service(
        self,
        name: str,
        timeout: float | None = None,
    ) -> ServiceStream:
        """Stop a service.

        Args:
            name: The name of the service.
            timeout: Timeout in seconds before force stop.

        Returns:
            A stream of service log events.
        """
        from sprites.services import stop_service

        return stop_service(self, name, timeout)

    def signal_service(self, name: str, signal: str) -> None:
        """Send a signal to a running service.

        Args:
            name: The name of the service.
            signal: The signal to send (e.g., "SIGTERM", "SIGHUP").
        """
        from sprites.services import signal_service

        signal_service(self, name, signal)
