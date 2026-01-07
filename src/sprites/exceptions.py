"""Exceptions for the Sprites SDK."""


class SpriteError(Exception):
    """Base exception for all Sprites SDK errors."""

    pass


class APIError(SpriteError):
    """Raised when an API call fails."""

    def __init__(self, message: str, status_code: int | None = None, response: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ExitError(SpriteError):
    """Raised when a command exits with non-zero status."""

    def __init__(
        self, code: int, stdout: bytes = b"", stderr: bytes = b"", message: str | None = None
    ):
        self._code = code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message or f"exit status {code}")

    @property
    def returncode(self) -> int:
        """Return the exit code (alias for code)."""
        return self._code

    def exit_code(self) -> int:
        """Return the exit code."""
        return self._code


class TimeoutError(SpriteError):
    """Raised when a command times out."""

    def __init__(self, message: str = "command timed out", timeout: float | None = None):
        super().__init__(message)
        self.timeout = timeout


class ConnectionError(SpriteError):
    """Raised when a WebSocket connection fails."""

    pass
