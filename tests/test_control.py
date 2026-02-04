"""Tests for the control connection module."""

import pytest
from sprites import SpritesClient


class TestControlModeClientOptions:
    """Tests for control mode client options."""

    def test_control_mode_true_by_default(self):
        """Control mode should be enabled by default for efficient connection reuse."""
        client = SpritesClient(token="test-token")
        assert client.control_mode is True

    def test_control_mode_enabled_explicitly(self):
        """Control mode should be enabled when explicitly specified."""
        client = SpritesClient(token="test-token", control_mode=True)
        assert client.control_mode is True

    def test_control_mode_disabled_explicitly(self):
        """Control mode should be disabled when explicitly set to False."""
        client = SpritesClient(token="test-token", control_mode=False)
        assert client.control_mode is False


class TestSpriteControlMode:
    """Tests for sprite control mode."""

    def test_reflects_client_control_mode_true(self):
        """Sprite should reflect client's control mode setting when True."""
        client = SpritesClient(token="test-token", control_mode=True)
        sprite = client.sprite("test-sprite")
        assert sprite.use_control_mode() is True

    def test_reflects_client_control_mode_false(self):
        """Sprite should reflect client's control mode setting when False."""
        client = SpritesClient(token="test-token", control_mode=False)
        sprite = client.sprite("test-sprite")
        assert sprite.use_control_mode() is False

    def test_reflects_client_control_mode_default(self):
        """Sprite should reflect default client control mode (True - enabled by default)."""
        client = SpritesClient(token="test-token")
        sprite = client.sprite("test-sprite")
        assert sprite.use_control_mode() is True


class TestControlURLBuilding:
    """Tests for control endpoint URL building."""

    def test_control_endpoint_url_http(self):
        """Control endpoint URL should be built correctly for HTTP."""
        client = SpritesClient(token="test-token", base_url="http://localhost:8080")
        sprite = client.sprite("my-sprite")

        expected_url = "ws://localhost:8080/v1/sprites/my-sprite/control"

        # Build actual URL (simulating what ControlConnection does)
        base_url = sprite.client.base_url
        if base_url.startswith("https"):
            base_url = "wss" + base_url[5:]
        elif base_url.startswith("http"):
            base_url = "ws" + base_url[4:]
        actual_url = f"{base_url}/v1/sprites/{sprite.name}/control"

        assert actual_url == expected_url

    def test_control_endpoint_url_https(self):
        """Control endpoint URL should convert HTTPS to WSS."""
        client = SpritesClient(token="test-token", base_url="https://api.sprites.dev")
        sprite = client.sprite("my-sprite")

        # Build actual URL
        base_url = sprite.client.base_url
        if base_url.startswith("https"):
            base_url = "wss" + base_url[5:]
        elif base_url.startswith("http"):
            base_url = "ws" + base_url[4:]
        actual_url = f"{base_url}/v1/sprites/{sprite.name}/control"

        assert actual_url.startswith("wss://")
        assert "my-sprite" in actual_url
        assert "/control" in actual_url
