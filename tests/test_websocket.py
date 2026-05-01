"""Tests for WebSocket protocol handling."""

import json

import pytest

from sprites import SpritesClient
from sprites.exec import Cmd
from sprites.websocket import WSCommand


def _make_cmd(*, session_id: str | None = None, tty: bool = False) -> Cmd:
    client = SpritesClient(token="test-token")
    sprite = client.sprite("test-sprite")
    return Cmd(sprite, ["echo", "hello"], session_id=session_id, tty=tty)


class TestSessionInfoCapture:
    """The server sends a `session_info` message after the WebSocket connects.

    For NEW sessions it carries the server-assigned `session_id`. The SDK should
    populate `cmd.session_id` so callers can later reattach via
    `sprite.attach_session(cmd.session_id)`.
    """

    def test_populates_session_id_for_new_session_non_tty(self):
        cmd = _make_cmd()
        ws = WSCommand(cmd)
        message = json.dumps({
            "type": "session_info",
            "session_id": "12",
            "command": "echo",
            "tty": False,
        })

        ws._maybe_capture_session_info(message)

        assert cmd.session_id == "12"

    def test_populates_session_id_for_new_session_tty(self):
        cmd = _make_cmd(tty=True)
        ws = WSCommand(cmd)
        message = json.dumps({
            "type": "session_info",
            "session_id": "abc-123",
            "command": "bash",
            "tty": True,
        })

        ws._maybe_capture_session_info(message)

        assert cmd.session_id == "abc-123"

    def test_does_not_overwrite_existing_session_id(self):
        # When attaching, cmd.session_id is set by the caller before connect.
        # The server echoes session_info; we should leave the attach value alone.
        cmd = _make_cmd(session_id="caller-supplied-99")
        ws = WSCommand(cmd)
        message = json.dumps({
            "type": "session_info",
            "session_id": "server-echo-99",
            "tty": False,
        })

        ws._maybe_capture_session_info(message)

        assert cmd.session_id == "caller-supplied-99"

    def test_ignores_non_session_info_messages(self):
        cmd = _make_cmd()
        ws = WSCommand(cmd)
        for message in [
            json.dumps({"type": "debug", "msg": "session_created"}),
            json.dumps({"type": "notification", "level": "info"}),
        ]:
            ws._maybe_capture_session_info(message)

        assert cmd.session_id is None

    def test_ignores_non_json_messages(self):
        cmd = _make_cmd()
        ws = WSCommand(cmd)

        ws._maybe_capture_session_info("not json")
        ws._maybe_capture_session_info("")

        assert cmd.session_id is None

    def test_ignores_session_info_without_session_id_field(self):
        # Defensive: server should always include session_id, but if a future server
        # ever sends a session_info without it, we shouldn't crash.
        cmd = _make_cmd()
        ws = WSCommand(cmd)
        message = json.dumps({"type": "session_info", "tty": False})

        ws._maybe_capture_session_info(message)

        assert cmd.session_id is None

    def test_coerces_int_session_id_to_string(self):
        # The live server returns session_id as a string ("12"), but tolerate ints
        # in case the wire format ever changes.
        cmd = _make_cmd()
        ws = WSCommand(cmd)
        message = json.dumps({"type": "session_info", "session_id": 42})

        ws._maybe_capture_session_info(message)

        assert cmd.session_id == "42"

    @pytest.mark.asyncio
    async def test_handle_message_captures_session_info_non_tty(self):
        cmd = _make_cmd()
        ws = WSCommand(cmd)
        message = json.dumps({
            "type": "session_info",
            "session_id": "55",
            "tty": False,
        })

        await ws._handle_message(message)

        assert cmd.session_id == "55"

    @pytest.mark.asyncio
    async def test_handle_message_captures_session_info_tty(self):
        cmd = _make_cmd(tty=True)
        ws = WSCommand(cmd)
        message = json.dumps({
            "type": "session_info",
            "session_id": "tty-77",
            "tty": True,
        })

        await ws._handle_message(message)

        assert cmd.session_id == "tty-77"
