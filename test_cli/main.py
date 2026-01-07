#!/usr/bin/env python3
"""
Sprite SDK CLI - Test command-line interface for SDK validation.

Usage:
  test-cli [options] <command> [args...]
  test-cli create <sprite-name>
  test-cli destroy <sprite-name>
  test-cli -sprite <name> policy <subcommand> [args...]
  test-cli -sprite <name> checkpoint <subcommand> [args...]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Any

# Add parent directory to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class Logger:
    """Structured JSON logger."""

    def __init__(self, log_path: str | None = None):
        self.file = open(log_path, "a") if log_path else None

    def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        if not self.file:
            return
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        }
        self.file.write(json.dumps(event) + "\n")
        self.file.flush()

    def close(self) -> None:
        if self.file:
            self.file.close()


def parse_duration(s: str) -> float:
    """Parse a Go-style duration string (e.g., '10s', '5m', '1h') to seconds."""
    if not s or s == "0":
        return 0

    s = s.strip()
    total = 0.0
    current_num = ""

    i = 0
    while i < len(s):
        c = s[i]
        if c.isdigit() or c == ".":
            current_num += c
        else:
            if current_num:
                num = float(current_num)
                if c == "h":
                    total += num * 3600
                elif c == "m":
                    # Check for 'ms' (milliseconds)
                    if i + 1 < len(s) and s[i + 1] == "s":
                        total += num / 1000
                        i += 1
                    else:
                        total += num * 60
                elif c == "s":
                    total += num
                current_num = ""
        i += 1

    # Handle plain number (assume seconds)
    if current_num:
        total += float(current_num)

    return total


def parse_env(env_str: str) -> dict[str, str]:
    """Parse comma-separated key=value pairs."""
    if not env_str:
        return {}
    result = {}
    for pair in env_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key] = value
    return result


def create_sprite(token: str, base_url: str, name: str, logger: Logger) -> None:
    """Create a sprite."""
    from sprites import SpritesClient

    logger.log_event("sprite_create_start", {"sprite_name": name, "base_url": base_url})

    try:
        client = SpritesClient(token, base_url=base_url)
        sprite = client.create_sprite(name)
        logger.log_event("sprite_create_completed", {"sprite_name": sprite.name})
        print(f"Sprite '{sprite.name}' created successfully")
    except Exception as e:
        logger.log_event("sprite_create_failed", {"sprite_name": name, "error": str(e)})
        print(f"Failed to create sprite: {e}", file=sys.stderr)
        sys.exit(1)


def destroy_sprite(token: str, base_url: str, name: str, logger: Logger) -> None:
    """Destroy a sprite."""
    from sprites import SpritesClient

    logger.log_event("sprite_destroy_start", {"sprite_name": name, "base_url": base_url})

    try:
        client = SpritesClient(token, base_url=base_url)
        client.delete_sprite(name)
        logger.log_event("sprite_destroy_completed", {"sprite_name": name})
        print(f"Sprite '{name}' destroyed successfully")
    except Exception as e:
        logger.log_event("sprite_destroy_failed", {"sprite_name": name, "error": str(e)})
        print(f"Failed to destroy sprite: {e}", file=sys.stderr)
        sys.exit(1)


def handle_policy_command(
    token: str, base_url: str, sprite_name: str, args: list[str], logger: Logger
) -> None:
    """Handle policy subcommands."""
    from sprites import SpritesClient
    from sprites.types import NetworkPolicy, PolicyRule

    if not args:
        print("Error: policy subcommand required (get, set)", file=sys.stderr)
        sys.exit(1)

    client = SpritesClient(token, base_url=base_url)
    sprite = client.sprite(sprite_name)

    subcommand = args[0]
    if subcommand == "get":
        logger.log_event("policy_get_start", {"sprite": sprite_name})
        try:
            policy = sprite.get_network_policy()
            logger.log_event("policy_get_completed", {"rules_count": len(policy.rules)})
            output = {
                "rules": [
                    {k: v for k, v in asdict(r).items() if v is not None} for r in policy.rules
                ]
            }
            print(json.dumps(output, indent=2))
        except Exception as e:
            logger.log_event("policy_get_failed", {"error": str(e)})
            print(f"Failed to get network policy: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "set":
        if len(args) < 2:
            print("Error: policy JSON required (policy set '<json>')", file=sys.stderr)
            sys.exit(1)
        policy_json = args[1]
        try:
            policy_data = json.loads(policy_json)
        except json.JSONDecodeError as e:
            print(f"Invalid policy JSON: {e}", file=sys.stderr)
            sys.exit(1)

        rules = [PolicyRule(**r) for r in policy_data.get("rules", [])]
        policy = NetworkPolicy(rules=rules)

        logger.log_event("policy_set_start", {"sprite": sprite_name, "rules_count": len(rules)})
        try:
            sprite.update_network_policy(policy)
            logger.log_event("policy_set_completed", {"rules_count": len(rules)})
            print("Network policy updated")
        except Exception as e:
            logger.log_event("policy_set_failed", {"error": str(e)})
            print(f"Failed to set network policy: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown policy subcommand: {subcommand}", file=sys.stderr)
        sys.exit(1)


def handle_checkpoint_command(
    token: str, base_url: str, sprite_name: str, args: list[str], logger: Logger
) -> None:
    """Handle checkpoint subcommands."""
    from sprites import SpritesClient

    if not args:
        print("Error: checkpoint subcommand required (list, create, get, restore)", file=sys.stderr)
        sys.exit(1)

    client = SpritesClient(token, base_url=base_url)
    sprite = client.sprite(sprite_name)

    subcommand = args[0]
    if subcommand == "list":
        logger.log_event("checkpoint_list_start", {"sprite": sprite_name})
        try:
            checkpoints = sprite.list_checkpoints()
            logger.log_event("checkpoint_list_completed", {"count": len(checkpoints)})
            output = [
                {
                    "id": c.id,
                    "create_time": c.create_time.isoformat(),
                    "comment": c.comment,
                }
                for c in checkpoints
            ]
            print(json.dumps(output, indent=2))
        except Exception as e:
            logger.log_event("checkpoint_list_failed", {"error": str(e)})
            print(f"Failed to list checkpoints: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "create":
        comment = args[1] if len(args) > 1 else ""
        logger.log_event("checkpoint_create_start", {"sprite": sprite_name, "comment": comment})
        try:
            stream = sprite.create_checkpoint(comment)
            for msg in stream:
                print(json.dumps({"type": msg.type, "data": msg.data, "error": msg.error}))
            logger.log_event("checkpoint_create_completed", {"sprite": sprite_name})
        except Exception as e:
            logger.log_event("checkpoint_create_failed", {"error": str(e)})
            print(f"Failed to create checkpoint: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "get":
        if len(args) < 2:
            print("Error: checkpoint ID required", file=sys.stderr)
            sys.exit(1)
        checkpoint_id = args[1]
        logger.log_event(
            "checkpoint_get_start", {"sprite": sprite_name, "checkpoint": checkpoint_id}
        )
        try:
            checkpoint = sprite.get_checkpoint(checkpoint_id)
            logger.log_event("checkpoint_get_completed", {"checkpoint": checkpoint_id})
            output = {
                "id": checkpoint.id,
                "create_time": checkpoint.create_time.isoformat(),
                "comment": checkpoint.comment,
            }
            print(json.dumps(output, indent=2))
        except Exception as e:
            logger.log_event("checkpoint_get_failed", {"error": str(e)})
            print(f"Failed to get checkpoint: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "restore":
        if len(args) < 2:
            print("Error: checkpoint ID required", file=sys.stderr)
            sys.exit(1)
        checkpoint_id = args[1]
        logger.log_event(
            "checkpoint_restore_start", {"sprite": sprite_name, "checkpoint": checkpoint_id}
        )
        try:
            stream = sprite.restore_checkpoint(checkpoint_id)
            for msg in stream:
                print(json.dumps({"type": msg.type, "data": msg.data, "error": msg.error}))
            logger.log_event(
                "checkpoint_restore_completed",
                {"sprite": sprite_name, "checkpoint": checkpoint_id},
            )
        except Exception as e:
            logger.log_event("checkpoint_restore_failed", {"error": str(e)})
            print(f"Failed to restore checkpoint: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown checkpoint subcommand: {subcommand}", file=sys.stderr)
        sys.exit(1)


def execute_command(
    token: str,
    base_url: str,
    sprite_name: str,
    command: str,
    cmd_args: list[str],
    cwd: str | None,
    env: dict[str, str] | None,
    tty: bool,
    tty_rows: int,
    tty_cols: int,
    session_id: str | None,
    timeout: float | None,
    output_mode: str,
    logger: Logger,
) -> None:
    """Execute a command on the sprite."""
    from sprites import ExitError, SpritesClient
    from sprites.exceptions import TimeoutError

    logger.log_event(
        "command_start",
        {
            "sprite": sprite_name,
            "command": command,
            "args": cmd_args,
            "base_url": base_url,
            "tty": tty,
            "session_id": session_id,
            "timeout": str(timeout) if timeout else "0",
            "output": output_mode,
        },
    )

    client = SpritesClient(token, base_url=base_url)
    sprite = client.sprite(sprite_name)

    # Build command args
    all_args = [command] + cmd_args

    # Create command
    if session_id:
        cmd = sprite.attach_session(session_id, timeout=timeout)
        logger.log_event("session_attach", {"session_id": session_id})
    else:
        cmd = sprite.command(*all_args, env=env, cwd=cwd, timeout=timeout)

    # Configure TTY
    if tty:
        cmd.set_tty(True)
        cmd.set_tty_size(tty_rows, tty_cols)
        logger.log_event("tty_configured", {"rows": tty_rows, "cols": tty_cols})

    # Set text message handler for logging
    def handle_text_message(data: bytes) -> None:
        try:
            msg = json.loads(data.decode())
            logger.log_event("text_message", {"message_type": msg.get("type"), "data": msg})
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.log_event("text_message", {"raw_data": data.decode(errors="replace")})

    cmd._text_message_handler = handle_text_message

    # Execute based on output mode
    try:
        if output_mode == "stdout":
            output = cmd.output()
            # Write raw bytes to stdout
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
            logger.log_event("command_completed", {"exit_code": 0, "output_length": len(output)})
        elif output_mode == "combined":
            output = cmd.combined_output()
            # Write raw bytes to stdout
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
            logger.log_event("command_completed", {"exit_code": 0, "output_length": len(output)})
        elif output_mode == "exit-code":
            cmd.run()
            logger.log_event("command_completed", {"exit_code": 0})
        else:
            # Default streaming mode
            cmd.stdout = sys.stdout.buffer
            cmd.stderr = sys.stderr.buffer
            cmd.stdin = sys.stdin.buffer
            cmd.run()
            logger.log_event("command_completed", {"exit_code": 0})
    except ExitError as e:
        exit_code = e.exit_code()
        logger.log_event("command_completed", {"exit_code": exit_code})
        # For stdout/combined modes, print any captured output
        if output_mode in ("stdout", "combined") and e.stdout:
            sys.stdout.buffer.write(e.stdout)
            sys.stdout.buffer.flush()
        sys.exit(exit_code)
    except TimeoutError as e:
        logger.log_event("command_timeout", {"error": str(e), "timeout": timeout})
        print(f"Command timed out: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.log_event("command_failed", {"error": str(e)})
        print(f"Command failed: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    # Custom argument parser to handle Go-style flags with dashes
    parser = argparse.ArgumentParser(
        description="Sprite SDK CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-base-url", default="https://api.sprites.dev", help="Base URL for the sprite API")
    parser.add_argument("-sprite", help="Sprite name for exec commands")
    parser.add_argument("-dir", help="Working directory for command")
    parser.add_argument("-env", help="Environment variables (comma-separated key=value)")
    parser.add_argument("-tty", action="store_true", help="Enable TTY mode")
    parser.add_argument("-tty-rows", type=int, default=24, help="TTY rows")
    parser.add_argument("-tty-cols", type=int, default=80, help="TTY cols")
    parser.add_argument("-session-id", help="Attach to existing session")
    parser.add_argument("-timeout", default="0", help="Command timeout (e.g., 10s, 5m)")
    parser.add_argument(
        "-output",
        default="stdout",
        choices=["stdout", "combined", "exit-code"],
        help="Output mode",
    )
    parser.add_argument("-log-target", help="File for structured JSON logs")
    parser.add_argument("command", nargs="?", help="Command to execute")
    parser.add_argument("args", nargs="*", help="Command arguments")

    # Parse known args to handle variable command args
    args, unknown = parser.parse_known_args()

    # Combine remaining args with known args
    cmd_args = args.args + unknown

    # Initialize logger
    logger = Logger(getattr(args, "log_target", None))

    # Get token from environment variable
    token = os.environ.get("SPRITES_TOKEN")
    if not token:
        print("Error: SPRITES_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    base_url = getattr(args, "base_url", "https://api.sprites.dev")

    # Handle special commands
    if args.command == "create":
        if not cmd_args:
            print("Error: sprite name is required for create command", file=sys.stderr)
            sys.exit(1)
        create_sprite(token, base_url, cmd_args[0], logger)
        return

    if args.command == "destroy":
        if not cmd_args:
            print("Error: sprite name is required for destroy command", file=sys.stderr)
            sys.exit(1)
        destroy_sprite(token, base_url, cmd_args[0], logger)
        return

    if args.command == "policy":
        sprite_name = getattr(args, "sprite", None)
        if not sprite_name:
            print("Error: -sprite is required for policy command", file=sys.stderr)
            sys.exit(1)
        handle_policy_command(token, base_url, sprite_name, cmd_args, logger)
        return

    if args.command == "checkpoint":
        sprite_name = getattr(args, "sprite", None)
        if not sprite_name:
            print("Error: -sprite is required for checkpoint command", file=sys.stderr)
            sys.exit(1)
        handle_checkpoint_command(token, base_url, sprite_name, cmd_args, logger)
        return

    # For exec commands, sprite name is required
    sprite_name = getattr(args, "sprite", None)
    if not sprite_name:
        print("Error: -sprite is required for exec commands", file=sys.stderr)
        sys.exit(1)

    if not args.command:
        print("Error: command is required", file=sys.stderr)
        sys.exit(1)

    # Parse timeout
    timeout_str = getattr(args, "timeout", "0")
    timeout = parse_duration(timeout_str)
    if timeout <= 0:
        timeout = None

    # Execute command
    execute_command(
        token=token,
        base_url=base_url,
        sprite_name=sprite_name,
        command=args.command,
        cmd_args=cmd_args,
        cwd=getattr(args, "dir", None),
        env=parse_env(getattr(args, "env", None) or ""),
        tty=args.tty,
        tty_rows=getattr(args, "tty_rows", 24),
        tty_cols=getattr(args, "tty_cols", 80),
        session_id=getattr(args, "session_id", None),
        timeout=timeout,
        output_mode=args.output,
        logger=logger,
    )


if __name__ == "__main__":
    main()
