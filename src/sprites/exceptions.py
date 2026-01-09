"""
Exceptions for the Sprites SDK
"""

from typing import Optional


class SpriteError(Exception):
    """Base exception for all Sprite SDK errors."""
    pass


class NetworkError(SpriteError):
    """Error during network communication."""
    pass


class AuthenticationError(SpriteError):
    """Authentication failed."""
    pass


class NotFoundError(SpriteError):
    """Resource not found."""
    pass


class ExecError(SpriteError):
    """Command execution failed with non-zero exit code."""

    def __init__(
        self,
        message: str,
        exit_code: int,
        stdout: bytes = b"",
        stderr: bytes = b""
    ):
        super().__init__(message)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class FilesystemError(SpriteError):
    """Error during filesystem operation."""

    def __init__(
        self,
        message: str,
        operation: str,
        path: str,
        code: Optional[str] = None
    ):
        super().__init__(message)
        self.operation = operation
        self.path = path
        self.code = code

    def __str__(self) -> str:
        if self.code:
            return f"{self.operation} {self.path}: {self.args[0]} ({self.code})"
        return f"{self.operation} {self.path}: {self.args[0]}"


class FileNotFoundError_(FilesystemError):
    """File or directory not found."""

    def __init__(self, operation: str, path: str):
        super().__init__("file not found", operation, path, "ENOENT")


class IsADirectoryError_(FilesystemError):
    """Expected file but found directory."""

    def __init__(self, operation: str, path: str):
        super().__init__("is a directory", operation, path, "EISDIR")


class NotADirectoryError_(FilesystemError):
    """Expected directory but found file."""

    def __init__(self, operation: str, path: str):
        super().__init__("not a directory", operation, path, "ENOTDIR")


class PermissionError_(FilesystemError):
    """Permission denied."""

    def __init__(self, operation: str, path: str):
        super().__init__("permission denied", operation, path, "EACCES")


class FileExistsError_(FilesystemError):
    """File already exists."""

    def __init__(self, operation: str, path: str):
        super().__init__("file exists", operation, path, "EEXIST")


class DirectoryNotEmptyError(FilesystemError):
    """Directory is not empty."""

    def __init__(self, operation: str, path: str):
        super().__init__("directory not empty", operation, path, "ENOTEMPTY")
