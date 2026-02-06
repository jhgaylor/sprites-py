"""
Sprites client implementation
"""

from typing import Any, Dict, List, Optional
import httpx

from .types import (
    ClientOptions,
    SpriteConfig,
    SpriteInfo,
    SpriteList,
    ListOptions,
    URLSettings,
)
from .exceptions import (
    SpriteError,
    NetworkError,
    AuthenticationError,
    NotFoundError,
)


class SpritesClient:
    """Main client for interacting with the Sprites API."""

    def __init__(
        self,
        token: str,
        base_url: str = "https://api.sprites.dev",
        timeout: float = 30.0
    ):
        """
        Initialize the Sprites client.

        Args:
            token: Authentication token
            base_url: Base URL for the API (default: https://api.sprites.dev)
            timeout: HTTP request timeout in seconds (default: 30.0)
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "SpritesClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    @property
    def http_client(self) -> "_AuthenticatedClient":
        """Get an HTTP client with pre-configured authorization headers."""
        return _AuthenticatedClient(self._client, self.token)

    def _headers(self) -> Dict[str, str]:
        """Get default headers with authorization."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response, operation: str) -> None:
        """Handle HTTP response errors."""
        if response.status_code == 401:
            raise AuthenticationError(f"Authentication failed for {operation}")
        if response.status_code == 404:
            raise NotFoundError(f"Resource not found for {operation}")
        if not response.is_success:
            try:
                body = response.text
            except Exception:
                body = ""
            raise SpriteError(
                f"Failed {operation} (status {response.status_code}): {body}"
            )

    def sprite(self, name: str) -> "Sprite":
        """
        Get a handle to a sprite (doesn't create it on the server).

        Args:
            name: Sprite name

        Returns:
            Sprite instance
        """
        from .sprite import Sprite
        return Sprite(name, self)

    def create_sprite(
        self,
        name: str,
        config: Optional[SpriteConfig] = None
    ) -> "Sprite":
        """
        Create a new sprite.

        Args:
            name: Sprite name
            config: Optional configuration

        Returns:
            Created Sprite instance
        """
        from .sprite import Sprite

        request: Dict[str, Any] = {"name": name}
        if config:
            request["config"] = {
                k: v for k, v in {
                    "ram_mb": config.ram_mb,
                    "cpus": config.cpus,
                    "region": config.region,
                    "storage_gb": config.storage_gb,
                }.items() if v is not None
            }

        try:
            response = self._client.post(
                f"{self.base_url}/v1/sprites",
                headers=self._headers(),
                json=request,
                timeout=120.0,  # 2 minute timeout for creation
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error creating sprite: {e}")

        self._handle_response(response, "create sprite")
        result = response.json()
        return Sprite(result["name"], self)

    def get_sprite(self, name: str) -> "Sprite":
        """
        Get information about a sprite.

        Args:
            name: Sprite name

        Returns:
            Sprite instance with populated info
        """
        from .sprite import Sprite

        try:
            response = self._client.get(
                f"{self.base_url}/v1/sprites/{name}",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error getting sprite: {e}")

        self._handle_response(response, f"get sprite '{name}'")
        info = response.json()
        sprite = Sprite(info["name"], self)
        sprite._update_from_info(info)
        return sprite

    def list_sprites(self, options: Optional[ListOptions] = None) -> SpriteList:
        """
        List sprites with optional filtering and pagination.

        Args:
            options: Optional filtering/pagination options

        Returns:
            Paginated list of sprites
        """
        params: Dict[str, Any] = {}
        if options:
            if options.max_results:
                params["max_results"] = options.max_results
            if options.continuation_token:
                params["continuation_token"] = options.continuation_token
            if options.prefix:
                params["prefix"] = options.prefix

        try:
            response = self._client.get(
                f"{self.base_url}/v1/sprites",
                headers=self._headers(),
                params=params,
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error listing sprites: {e}")

        self._handle_response(response, "list sprites")
        data = response.json()

        sprites = []
        for s in data.get("sprites", []):
            sprites.append(SpriteInfo(
                id=s.get("id", ""),
                name=s.get("name", ""),
                organization=s.get("organization", ""),
                status=s.get("status", ""),
                url=s.get("url"),
                primary_region=s.get("primary_region"),
            ))

        return SpriteList(
            sprites=sprites,
            has_more=data.get("hasMore", False),
            next_continuation_token=data.get("nextContinuationToken"),
        )

    def list_all_sprites(self, prefix: Optional[str] = None) -> List["Sprite"]:
        """
        List all sprites, handling pagination automatically.

        Args:
            prefix: Optional name prefix filter

        Returns:
            List of all Sprite instances
        """
        from .sprite import Sprite

        all_sprites: List[Sprite] = []
        continuation_token: Optional[str] = None

        while True:
            result = self.list_sprites(ListOptions(
                prefix=prefix,
                max_results=100,
                continuation_token=continuation_token,
            ))

            for info in result.sprites:
                sprite = Sprite(info.name, self)
                all_sprites.append(sprite)

            if not result.has_more:
                break
            continuation_token = result.next_continuation_token

        return all_sprites

    def delete_sprite(self, name: str) -> None:
        """
        Delete a sprite.

        Args:
            name: Sprite name
        """
        try:
            response = self._client.delete(
                f"{self.base_url}/v1/sprites/{name}",
                headers=self._headers(),
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error deleting sprite: {e}")

        if response.status_code != 204:
            self._handle_response(response, f"delete sprite '{name}'")

    def upgrade_sprite(self, name: str) -> None:
        """
        Upgrade a sprite to the latest version.

        Args:
            name: Sprite name
        """
        try:
            response = self._client.post(
                f"{self.base_url}/v1/sprites/{name}/upgrade",
                headers=self._headers(),
                timeout=60.0,
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error upgrading sprite: {e}")

        if response.status_code != 204:
            self._handle_response(response, f"upgrade sprite '{name}'")

    def update_url_settings(self, name: str, settings: URLSettings) -> None:
        """
        Update URL authentication settings for a sprite.

        Args:
            name: Sprite name
            settings: URL settings with auth: "public" for no auth, "sprite" for authenticated
        """
        try:
            response = self._client.put(
                f"{self.base_url}/v1/sprites/{name}",
                headers=self._headers(),
                json={"url_settings": {"auth": settings.auth}},
            )
        except httpx.RequestError as e:
            raise NetworkError(f"Network error updating URL settings: {e}")

        self._handle_response(response, f"update URL settings for '{name}'")

    @staticmethod
    def create_token(
        fly_macaroon: str,
        org_slug: str,
        invite_code: Optional[str] = None
    ) -> str:
        """
        Create a sprite access token using a Fly.io macaroon token.

        Args:
            fly_macaroon: Fly.io macaroon token
            org_slug: Organization slug
            invite_code: Optional invite code

        Returns:
            Access token string
        """
        api_url = "https://api.sprites.dev"
        url = f"{api_url}/v1/organizations/{org_slug}/tokens"

        body: Dict[str, Any] = {"description": "Sprite SDK Token"}
        if invite_code:
            body["invite_code"] = invite_code

        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"FlyV1 {fly_macaroon}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            except httpx.RequestError as e:
                raise NetworkError(f"Network error creating token: {e}")

            if not response.is_success:
                raise SpriteError(
                    f"API returned status {response.status_code}: {response.text}"
                )

            result = response.json()
            if "token" not in result:
                raise SpriteError("No token returned in response")

            return result["token"]


class _AuthenticatedClient:
    """Wrapper around httpx.Client that adds authorization headers to all requests."""

    def __init__(self, client: httpx.Client, token: str):
        self._client = client
        self._token = token

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        return self._client.get(url, headers=headers, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        return self._client.post(url, headers=headers, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        return self._client.put(url, headers=headers, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self._auth_headers())
        return self._client.delete(url, headers=headers, **kwargs)
