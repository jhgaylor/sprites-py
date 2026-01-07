"""HTTP client for the Sprites API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from sprites.exceptions import APIError
from sprites.types import SpriteConfig, SpriteInfo, URLSettings

if TYPE_CHECKING:
    from sprites.sprite import Sprite

DEFAULT_BASE_URL = "https://api.sprites.dev"
DEFAULT_TIMEOUT = 30.0
CREATE_TIMEOUT = 120.0  # Sprite creation can take longer


class SpritesClient:
    """Client for interacting with the Sprites API."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Initialize a new Sprites client.

        Args:
            token: Authentication token for the API.
            base_url: Base URL for the API (default: https://api.sprites.dev).
            timeout: Default timeout for requests in seconds (default: 30).
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http_client: httpx.Client | None = None

    @property
    def http_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=self.timeout,
                headers={"Authorization": f"Bearer {self.token}"},
            )
        return self._http_client

    def sprite(self, name: str) -> Sprite:
        """Get a handle to a sprite (doesn't create it on the server).

        Args:
            name: The name of the sprite.

        Returns:
            A Sprite object for the given name.
        """
        from sprites.sprite import Sprite

        return Sprite(name=name, client=self)

    def create_sprite(self, name: str, config: SpriteConfig | None = None) -> Sprite:
        """Create a new sprite on the server.

        Args:
            name: The name of the sprite to create.
            config: Optional configuration for the sprite.

        Returns:
            A Sprite object for the created sprite.

        Raises:
            APIError: If the API call fails.
        """
        from sprites.sprite import Sprite

        url = f"{self.base_url}/v1/sprites"

        payload: dict[str, Any] = {"name": name}
        if config:
            cfg: dict[str, Any] = {}
            if config.ram_mb is not None:
                cfg["ram_mb"] = config.ram_mb
            if config.cpus is not None:
                cfg["cpus"] = config.cpus
            if config.region is not None:
                cfg["region"] = config.region
            if config.storage_gb is not None:
                cfg["storage_gb"] = config.storage_gb
            if cfg:
                payload["config"] = cfg

        try:
            response = self.http_client.post(
                url,
                json=payload,
                timeout=CREATE_TIMEOUT,
            )
        except httpx.RequestError as e:
            raise APIError(f"Failed to create sprite: {e}") from e

        if response.status_code != 201:
            raise APIError(
                f"Failed to create sprite (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        data = response.json()
        return Sprite(name=data.get("name", name), client=self)

    def get_sprite(self, name: str) -> Sprite:
        """Get information about a sprite.

        Args:
            name: The name of the sprite.

        Returns:
            A Sprite object with populated info.

        Raises:
            APIError: If the API call fails.
        """
        from sprites.sprite import Sprite

        url = f"{self.base_url}/v1/sprites/{name}"

        try:
            response = self.http_client.get(url)
        except httpx.RequestError as e:
            raise APIError(f"Failed to get sprite: {e}") from e

        if response.status_code == 404:
            raise APIError(f"Sprite not found: {name}", status_code=404)

        if response.status_code != 200:
            raise APIError(
                f"Failed to get sprite (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        data = response.json()
        info = SpriteInfo(
            name=data.get("name", name),
            id=data.get("id"),
            status=data.get("status"),
            url=data.get("url"),
            region=data.get("primary_region"),
        )
        return Sprite(name=info.name, client=self, info=info)

    def delete_sprite(self, name: str) -> None:
        """Delete a sprite.

        Args:
            name: The name of the sprite to delete.

        Raises:
            APIError: If the API call fails.
        """
        url = f"{self.base_url}/v1/sprites/{name}"

        try:
            response = self.http_client.delete(url)
        except httpx.RequestError as e:
            raise APIError(f"Failed to delete sprite: {e}") from e

        if response.status_code not in (200, 204):
            raise APIError(
                f"Failed to delete sprite (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

    def list_sprites(self, prefix: str = "") -> list[SpriteInfo]:
        """List all sprites.

        Args:
            prefix: Optional prefix to filter sprite names.

        Returns:
            List of SpriteInfo objects.

        Raises:
            APIError: If the API call fails.
        """
        url = f"{self.base_url}/v1/sprites"
        params = {}
        if prefix:
            params["prefix"] = prefix

        try:
            response = self.http_client.get(url, params=params)
        except httpx.RequestError as e:
            raise APIError(f"Failed to list sprites: {e}") from e

        if response.status_code != 200:
            raise APIError(
                f"Failed to list sprites (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        data = response.json()
        sprites_data = data.get("sprites", [])

        sprites = []
        for s in sprites_data:
            sprites.append(SpriteInfo(
                name=s.get("name", ""),
                id=s.get("id"),
                status=s.get("status"),
                url=s.get("url"),
            ))
        return sprites

    def update_url_settings(self, name: str, settings: URLSettings) -> None:
        """Update URL settings for a sprite.

        Args:
            name: The name of the sprite.
            settings: The URL settings to apply.

        Raises:
            APIError: If the API call fails.
        """
        url = f"{self.base_url}/v1/sprites/{name}"

        payload = {
            "url_settings": {
                "auth": settings.auth,
            }
        }

        try:
            response = self.http_client.put(url, json=payload)
        except httpx.RequestError as e:
            raise APIError(f"Failed to update URL settings: {e}") from e

        if response.status_code not in (200, 204):
            raise APIError(
                f"Failed to update URL settings (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

    def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> SpritesClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
