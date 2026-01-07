"""Pytest configuration for Sprites SDK tests."""

import os

import pytest


@pytest.fixture
def sprites_token() -> str:
    """Get the Sprites test token from environment."""
    token = os.environ.get("SPRITES_TEST_TOKEN")
    if not token:
        pytest.skip("SPRITES_TEST_TOKEN not set")
    return token


@pytest.fixture
def base_url() -> str:
    """Get the Sprites API base URL."""
    return os.environ.get("SPRITES_BASE_URL", "https://api.sprites.dev")
