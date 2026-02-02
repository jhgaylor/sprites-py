"""Control connection for multiplexed operations over a single WebSocket."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, Dict, Optional, Callable
from urllib.parse import urlencode

import websockets
from websockets.exceptions import ConnectionClosed

if TYPE_CHECKING:
    from .sprite import Sprite

# Control envelope protocol constants (must match server's pkg/wss)
CONTROL_PREFIX = "control:"
TYPE_OP_START = "op.start"
TYPE_OP_COMPLETE = "op.complete"
TYPE_OP_ERROR = "op.error"

# WebSocket keepalive timeouts
WS_PING_INTERVAL = 15  # seconds
WS_PONG_WAIT = 45  # seconds


class StreamID:
    """Stream identifiers for the binary protocol."""
    STDIN = 0
    STDOUT = 1
    STDERR = 2
    EXIT = 3
    STDIN_EOF = 4


class OpConn:
    """Represents an active operation on a control connection."""

    def __init__(self, cc: ControlConnection, tty: bool = False):
        """Initialize an operation connection.

        Args:
            cc: Parent control connection
            tty: Whether TTY mode is enabled
        """
        self.cc = cc
        self.tty = tty
        self.closed = False
        self.exit_code = -1
        self._done_event = asyncio.Event()

        # Output buffers
        self._stdout_buffer: bytearray = bytearray()
        self._stderr_buffer: bytearray = bytearray()

        # Callbacks
        self.on_stdout: Optional[Callable[[bytes], None]] = None
        self.on_stderr: Optional[Callable[[bytes], None]] = None
        self.on_message: Optional[Callable[[dict], None]] = None

    async def write(self, data: bytes) -> None:
        """Write data to the operation (stdin).

        Args:
            data: Data to write
        """
        if self.closed:
            raise RuntimeError("Operation closed")

        if self.tty:
            # PTY mode - send raw data
            await self.cc._send_data(data)
        else:
            # Non-PTY mode - prepend stream ID
            message = bytes([StreamID.STDIN]) + data
            await self.cc._send_data(message)

    async def send_eof(self) -> None:
        """Send stdin EOF."""
        if self.closed or self.tty:
            return
        await self.cc._send_data(bytes([StreamID.STDIN_EOF]))

    async def resize(self, cols: int, rows: int) -> None:
        """Send resize control message (TTY only).

        Args:
            cols: Number of columns
            rows: Number of rows
        """
        if not self.tty:
            return
        msg = json.dumps({"type": "resize", "cols": cols, "rows": rows})
        await self.cc._send_text(msg)

    async def signal(self, sig: str) -> None:
        """Send signal to remote process.

        Args:
            sig: Signal name (e.g., "TERM", "INT")
        """
        msg = json.dumps({"type": "signal", "signal": sig})
        await self.cc._send_text(msg)

    def handle_data(self, data: bytes) -> None:
        """Handle incoming data frame.

        Args:
            data: Incoming data
        """
        if self.tty:
            # PTY mode - emit raw output
            self._stdout_buffer.extend(data)
            if self.on_stdout:
                self.on_stdout(data)
        else:
            # Non-PTY mode - parse stream prefix
            if not data:
                return

            stream_id = data[0]
            payload = data[1:]

            if stream_id == StreamID.STDOUT:
                self._stdout_buffer.extend(payload)
                if self.on_stdout:
                    self.on_stdout(payload)
            elif stream_id == StreamID.STDERR:
                self._stderr_buffer.extend(payload)
                if self.on_stderr:
                    self.on_stderr(payload)
            elif stream_id == StreamID.EXIT:
                self.exit_code = payload[0] if payload else 0
                self.close()

    def handle_text(self, data: str) -> None:
        """Handle text message (session_info, notifications, etc.).

        Args:
            data: Text message data
        """
        try:
            msg = json.loads(data)
            if self.on_message:
                self.on_message(msg)
        except json.JSONDecodeError:
            pass

    def complete(self, exit_code: Optional[int] = None) -> None:
        """Mark operation as complete.

        Args:
            exit_code: Optional exit code
        """
        if self.closed:
            return
        self.closed = True
        if exit_code is not None:
            self.exit_code = exit_code
        self._done_event.set()

    def close(self) -> None:
        """Close the operation."""
        if self.closed:
            return
        self.closed = True
        self._done_event.set()

    def is_closed(self) -> bool:
        """Check if operation is closed."""
        return self.closed

    def get_exit_code(self) -> int:
        """Get exit code (-1 if not exited)."""
        return self.exit_code

    async def wait(self) -> int:
        """Wait for operation to complete.

        Returns:
            Exit code
        """
        if self.closed:
            return self.exit_code
        await self._done_event.wait()
        return self.exit_code

    def get_stdout(self) -> bytes:
        """Get accumulated stdout buffer."""
        return bytes(self._stdout_buffer)

    def get_stderr(self) -> bytes:
        """Get accumulated stderr buffer."""
        return bytes(self._stderr_buffer)


class ControlConnection:
    """Manages a persistent WebSocket connection for multiplexed operations."""

    def __init__(self, sprite: Sprite):
        """Initialize a control connection.

        Args:
            sprite: The sprite this connection is for
        """
        self.sprite = sprite
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.op_active = False
        self.op_conn: OpConn | None = None
        self.closed = False
        self.close_error: Optional[Exception] = None
        self._read_task: Optional[asyncio.Task[None]] = None

    async def connect(self) -> None:
        """Connect to the control endpoint."""
        if self.ws is not None:
            raise RuntimeError("Already connected")

        # Build WebSocket URL
        base_url = self.sprite.client.base_url
        if base_url.startswith("https"):
            base_url = "wss" + base_url[5:]
        elif base_url.startswith("http"):
            base_url = "ws" + base_url[4:]

        url = f"{base_url}/v1/sprites/{self.sprite.name}/control"
        headers = {"Authorization": f"Bearer {self.sprite.client.token}"}

        self.ws = await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=WS_PING_INTERVAL,
            ping_timeout=WS_PONG_WAIT,
            max_size=10 * 1024 * 1024,  # 10MB
        )

        # Start read loop
        self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Read messages from WebSocket."""
        if self.ws is None:
            return

        try:
            async for message in self.ws:
                await self._handle_message(message)
        except ConnectionClosed as e:
            self.close_error = e
        except Exception as e:
            self.close_error = e
        finally:
            self.closed = True
            if self.op_conn is not None:
                self.op_conn.close()

    async def _handle_message(self, message: str | bytes) -> None:
        """Handle incoming WebSocket message.

        Args:
            message: Incoming message
        """
        # Check for control message
        if isinstance(message, str) and message.startswith(CONTROL_PREFIX):
            payload = message[len(CONTROL_PREFIX):]
            try:
                msg = json.loads(payload)
                self._handle_control_message(msg)
            except json.JSONDecodeError:
                pass
            return

        # Data frame - deliver to active operation
        if self.op_conn is not None:
            if isinstance(message, str):
                self.op_conn.handle_text(message)
            else:
                self.op_conn.handle_data(message)

    def _handle_control_message(self, msg: Dict[str, Any]) -> None:
        """Handle control envelope message.

        Args:
            msg: Parsed control message
        """
        msg_type = msg.get("type", "")

        if msg_type == TYPE_OP_COMPLETE:
            if self.op_conn is not None:
                exit_code = msg.get("args", {}).get("exitCode", 0)
                self.op_conn.complete(exit_code)
            self.op_active = False
            self.op_conn = None

        elif msg_type == TYPE_OP_ERROR:
            if self.op_conn is not None:
                error = msg.get("args", {}).get("error", "unknown error")
                # Store error in stderr buffer
                self.op_conn._stderr_buffer.extend(f"Error: {error}\n".encode())
                self.op_conn.complete()
            self.op_active = False
            self.op_conn = None

    async def start_op(
        self,
        op: str,
        cmd: Optional[list[str]] = None,
        env: Optional[Dict[str, str]] = None,
        dir: Optional[str] = None,
        tty: bool = False,
        rows: int = 24,
        cols: int = 80,
        stdin: bool = True,
    ) -> OpConn:
        """Start a new operation.

        Args:
            op: Operation name (e.g., "exec")
            cmd: Command and arguments
            env: Environment variables
            dir: Working directory
            tty: Enable TTY mode
            rows: TTY rows
            cols: TTY columns
            stdin: Whether stdin is expected

        Returns:
            OpConn for the operation
        """
        if self.closed:
            raise RuntimeError(f"Control connection closed: {self.close_error}")

        if self.op_active:
            raise RuntimeError("Operation already in progress")

        if self.ws is None:
            raise RuntimeError("WebSocket not connected")

        self.op_active = True
        op_conn = OpConn(self, tty)
        self.op_conn = op_conn

        # Build args for the control message
        args: Dict[str, Any] = {}
        if cmd:
            args["cmd"] = cmd
        if env:
            env_list = [f"{k}={v}" for k, v in env.items()]
            args["env"] = env_list
        if dir:
            args["dir"] = dir
        if tty:
            args["tty"] = "true"
            args["rows"] = str(rows)
            args["cols"] = str(cols)
        args["stdin"] = "true" if stdin else "false"

        # Send op.start
        ctrl_msg = {
            "type": TYPE_OP_START,
            "op": op,
            "args": args,
        }
        frame = CONTROL_PREFIX + json.dumps(ctrl_msg)
        await self.ws.send(frame)

        return op_conn

    async def _send_data(self, data: bytes) -> None:
        """Send data frame.

        Args:
            data: Data to send
        """
        if self.ws is None or self.ws.state != websockets.protocol.State.OPEN:
            raise RuntimeError("WebSocket not connected")
        await self.ws.send(data)

    async def _send_text(self, data: str) -> None:
        """Send text frame.

        Args:
            data: Text to send
        """
        if self.ws is None or self.ws.state != websockets.protocol.State.OPEN:
            raise RuntimeError("WebSocket not connected")
        await self.ws.send(data)

    async def close(self) -> None:
        """Close the control connection."""
        if self.op_conn is not None:
            self.op_conn.close()
        if self.ws is not None:
            await self.ws.close()
            self.ws = None
        self.closed = True

        # Cancel read task
        if self._read_task is not None:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

    def is_closed(self) -> bool:
        """Check if connection is closed."""
        return self.closed


# Module-level cache for control connections
_control_connections: Dict[str, ControlConnection] = {}


async def get_control_connection(sprite: Sprite) -> ControlConnection:
    """Get or create a control connection for a sprite.

    Args:
        sprite: The sprite to connect to

    Returns:
        ControlConnection instance
    """
    key = f"{sprite.client.base_url}:{sprite.name}"

    # Return existing connection if valid
    if key in _control_connections:
        cc = _control_connections[key]
        if not cc.is_closed():
            return cc

    # Create new connection
    cc = ControlConnection(sprite)
    await cc.connect()
    _control_connections[key] = cc

    return cc


async def close_control_connection(sprite: Sprite) -> None:
    """Close the control connection for a sprite.

    Args:
        sprite: The sprite whose connection to close
    """
    key = f"{sprite.client.base_url}:{sprite.name}"

    if key in _control_connections:
        cc = _control_connections.pop(key)
        await cc.close()
