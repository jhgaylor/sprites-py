#!/usr/bin/env python3
"""
Test CLI for Sprites Python SDK

Usage:
    python -m test_cli <command> [options]

Commands:
    create <sprite-name>          Create a new sprite
    destroy <sprite-name>         Destroy a sprite
    list                          List all sprites

    # Filesystem commands (require --sprite)
    fs-read <path>                Read file contents
    fs-write <path> <content>     Write content to file
    fs-list <path>                List directory contents
    fs-stat <path>                Get file/directory stats
    fs-mkdir <path>               Create directory
    fs-rm <path>                  Remove file or directory
    fs-rename <source> <dest>     Rename/move file or directory
    fs-copy <source> <dest>       Copy file or directory
    fs-chmod <path> <mode>        Change file permissions

    # Policy commands (require --sprite)
    policy-get                    Get network policy
    policy-set <json>             Set network policy

    # Checkpoint commands (require --sprite)
    checkpoint-list               List checkpoints
    checkpoint-create [comment]   Create checkpoint
    checkpoint-get <id>           Get checkpoint details
"""

import argparse
import json
import os
import sys
from typing import Optional

# Add parent directory to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sprites import SpritesClient, FilesystemError, NetworkPolicy, PolicyRule


def get_client() -> SpritesClient:
    """Get a SpritesClient using environment variables."""
    token = os.environ.get("SPRITES_TOKEN")
    if not token:
        print("Error: SPRITES_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    base_url = os.environ.get("SPRITES_BASE_URL", "https://api.sprites.dev")
    return SpritesClient(token=token, base_url=base_url)


def cmd_create(args: argparse.Namespace) -> None:
    """Create a new sprite."""
    client = get_client()
    sprite = client.create_sprite(args.name)
    print(f"Created sprite: {sprite.name}")


def cmd_destroy(args: argparse.Namespace) -> None:
    """Destroy a sprite."""
    client = get_client()
    client.delete_sprite(args.name)
    print(f"Destroyed sprite: {args.name}")


def cmd_list(args: argparse.Namespace) -> None:
    """List all sprites."""
    client = get_client()
    result = client.list_sprites()
    for sprite_info in result.sprites:
        print(f"{sprite_info.name} ({sprite_info.status})")


def cmd_fs_read(args: argparse.Namespace) -> None:
    """Read file contents."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    path = fs / args.path

    try:
        if args.binary:
            content = path.read_bytes()
            sys.stdout.buffer.write(content)
        else:
            content = path.read_text()
            print(content, end="")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_write(args: argparse.Namespace) -> None:
    """Write content to file."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    path = fs / args.path

    try:
        mode = int(args.mode, 8) if args.mode else 0o644
        if args.stdin:
            content = sys.stdin.read()
        else:
            content = args.content or ""

        path.write_text(content, mode=mode)
        print(f"Written: {args.path}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_list(args: argparse.Namespace) -> None:
    """List directory contents."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    path = fs / args.path

    try:
        if args.json:
            entries = []
            for entry in path.iterdir():
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "path": str(entry),
                        "is_dir": stat.is_dir,
                        "size": stat.size,
                        "mode": stat.mode,
                    })
                except FilesystemError:
                    entries.append({
                        "name": entry.name,
                        "path": str(entry),
                    })
            print(json.dumps({"path": str(path), "entries": entries, "count": len(entries)}))
        else:
            for entry in path.iterdir():
                try:
                    stat = entry.stat()
                    type_char = "d" if stat.is_dir else "-"
                    print(f"{type_char} {stat.mode:>6} {stat.size:>10} {entry.name}")
                except FilesystemError:
                    print(f"? {'?':>6} {'?':>10} {entry.name}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_stat(args: argparse.Namespace) -> None:
    """Get file/directory stats."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    path = fs / args.path

    try:
        stat = path.stat()
        if args.json:
            print(json.dumps({
                "name": stat.name,
                "path": stat.path,
                "size": stat.size,
                "mode": stat.mode,
                "mod_time": stat.mod_time.isoformat(),
                "is_dir": stat.is_dir,
            }))
        else:
            print(f"Name: {stat.name}")
            print(f"Path: {stat.path}")
            print(f"Size: {stat.size}")
            print(f"Mode: {stat.mode}")
            print(f"Modified: {stat.mod_time}")
            print(f"Type: {'directory' if stat.is_dir else 'file'}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_mkdir(args: argparse.Namespace) -> None:
    """Create directory."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    path = fs / args.path

    try:
        mode = int(args.mode, 8) if args.mode else 0o755
        path.mkdir(mode=mode, parents=args.parents, exist_ok=args.exist_ok)
        print(f"Created: {args.path}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_rm(args: argparse.Namespace) -> None:
    """Remove file or directory."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    path = fs / args.path

    try:
        if args.recursive:
            path.rmtree()
        else:
            path.unlink(missing_ok=args.force)
        print(f"Removed: {args.path}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_rename(args: argparse.Namespace) -> None:
    """Rename/move file or directory."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    source = fs / args.source
    dest = fs / args.dest

    try:
        result = source.rename(dest)
        print(f"Renamed: {args.source} -> {result}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_copy(args: argparse.Namespace) -> None:
    """Copy file or directory."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    source = fs / args.source
    dest = fs / args.dest

    try:
        result = source.copy_to(dest, recursive=args.recursive)
        print(f"Copied: {args.source} -> {result}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fs_chmod(args: argparse.Namespace) -> None:
    """Change file permissions."""
    client = get_client()
    sprite = client.sprite(args.sprite)
    fs = sprite.filesystem(args.workdir or "/")
    path = fs / args.path

    try:
        mode = int(args.mode, 8)
        path.chmod(mode, recursive=args.recursive)
        print(f"Changed mode: {args.path} -> {args.mode}")
    except FilesystemError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_policy_get(args: argparse.Namespace) -> None:
    """Get network policy."""
    client = get_client()
    sprite = client.sprite(args.sprite)

    policy = sprite.get_network_policy()
    rules = []
    for rule in policy.rules:
        r = {}
        if rule.domain:
            r["domain"] = rule.domain
        if rule.action:
            r["action"] = rule.action
        if rule.include:
            r["include"] = rule.include
        rules.append(r)
    print(json.dumps({"rules": rules}, indent=2))


def cmd_policy_set(args: argparse.Namespace) -> None:
    """Set network policy."""
    client = get_client()
    sprite = client.sprite(args.sprite)

    try:
        data = json.loads(args.policy)
        rules = []
        for r in data.get("rules", []):
            rules.append(PolicyRule(
                domain=r.get("domain"),
                action=r.get("action"),
                include=r.get("include"),
            ))
        policy = NetworkPolicy(rules=rules)
        sprite.update_network_policy(policy)
        print("Network policy updated")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_checkpoint_list(args: argparse.Namespace) -> None:
    """List checkpoints."""
    client = get_client()
    sprite = client.sprite(args.sprite)

    checkpoints = sprite.list_checkpoints()
    if args.json:
        result = []
        for cp in checkpoints:
            result.append({
                "id": cp.id,
                "create_time": cp.create_time.isoformat(),
                "comment": cp.comment,
            })
        print(json.dumps(result, indent=2))
    else:
        for cp in checkpoints:
            comment = f" - {cp.comment}" if cp.comment else ""
            print(f"{cp.id}: {cp.create_time}{comment}")


def cmd_checkpoint_create(args: argparse.Namespace) -> None:
    """Create checkpoint."""
    print("Checkpoint creation requires streaming support (not yet implemented)")
    sys.exit(1)


def cmd_checkpoint_get(args: argparse.Namespace) -> None:
    """Get checkpoint details."""
    client = get_client()
    sprite = client.sprite(args.sprite)

    cp = sprite.get_checkpoint(args.id)
    if args.json:
        print(json.dumps({
            "id": cp.id,
            "create_time": cp.create_time.isoformat(),
            "comment": cp.comment,
            "history": cp.history,
        }, indent=2))
    else:
        print(f"ID: {cp.id}")
        print(f"Created: {cp.create_time}")
        if cp.comment:
            print(f"Comment: {cp.comment}")
        if cp.history:
            print(f"History: {', '.join(cp.history)}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test CLI for Sprites Python SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sprite", "-s", help="Sprite name (required for most commands)")
    parser.add_argument("--workdir", "-w", help="Working directory for filesystem operations")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Sprite lifecycle commands
    create_parser = subparsers.add_parser("create", help="Create a new sprite")
    create_parser.add_argument("name", help="Sprite name")
    create_parser.set_defaults(func=cmd_create)

    destroy_parser = subparsers.add_parser("destroy", help="Destroy a sprite")
    destroy_parser.add_argument("name", help="Sprite name")
    destroy_parser.set_defaults(func=cmd_destroy)

    list_parser = subparsers.add_parser("list", help="List all sprites")
    list_parser.set_defaults(func=cmd_list)

    # Filesystem commands
    fs_read = subparsers.add_parser("fs-read", help="Read file contents")
    fs_read.add_argument("path", help="File path")
    fs_read.add_argument("--binary", "-b", action="store_true", help="Read as binary")
    fs_read.set_defaults(func=cmd_fs_read)

    fs_write = subparsers.add_parser("fs-write", help="Write content to file")
    fs_write.add_argument("path", help="File path")
    fs_write.add_argument("content", nargs="?", help="Content to write")
    fs_write.add_argument("--mode", "-m", help="File mode (octal, e.g., 0644)")
    fs_write.add_argument("--stdin", action="store_true", help="Read content from stdin")
    fs_write.set_defaults(func=cmd_fs_write)

    fs_list = subparsers.add_parser("fs-list", help="List directory contents")
    fs_list.add_argument("path", help="Directory path")
    fs_list.set_defaults(func=cmd_fs_list)

    fs_stat = subparsers.add_parser("fs-stat", help="Get file/directory stats")
    fs_stat.add_argument("path", help="File/directory path")
    fs_stat.set_defaults(func=cmd_fs_stat)

    fs_mkdir = subparsers.add_parser("fs-mkdir", help="Create directory")
    fs_mkdir.add_argument("path", help="Directory path")
    fs_mkdir.add_argument("--mode", "-m", help="Directory mode (octal, e.g., 0755)")
    fs_mkdir.add_argument("--parents", "-p", action="store_true", help="Create parent directories")
    fs_mkdir.add_argument("--exist-ok", action="store_true", help="Don't error if exists")
    fs_mkdir.set_defaults(func=cmd_fs_mkdir)

    fs_rm = subparsers.add_parser("fs-rm", help="Remove file or directory")
    fs_rm.add_argument("path", help="File/directory path")
    fs_rm.add_argument("--recursive", "-r", action="store_true", help="Remove recursively")
    fs_rm.add_argument("--force", "-f", action="store_true", help="Ignore if not exists")
    fs_rm.set_defaults(func=cmd_fs_rm)

    fs_rename = subparsers.add_parser("fs-rename", help="Rename/move file or directory")
    fs_rename.add_argument("source", help="Source path")
    fs_rename.add_argument("dest", help="Destination path")
    fs_rename.set_defaults(func=cmd_fs_rename)

    fs_copy = subparsers.add_parser("fs-copy", help="Copy file or directory")
    fs_copy.add_argument("source", help="Source path")
    fs_copy.add_argument("dest", help="Destination path")
    fs_copy.add_argument("--recursive", "-r", action="store_true", default=True,
                         help="Copy recursively (default)")
    fs_copy.set_defaults(func=cmd_fs_copy)

    fs_chmod = subparsers.add_parser("fs-chmod", help="Change file permissions")
    fs_chmod.add_argument("path", help="File/directory path")
    fs_chmod.add_argument("mode", help="New mode (octal, e.g., 0755)")
    fs_chmod.add_argument("--recursive", "-r", action="store_true", help="Apply recursively")
    fs_chmod.set_defaults(func=cmd_fs_chmod)

    # Policy commands
    policy_get = subparsers.add_parser("policy-get", help="Get network policy")
    policy_get.set_defaults(func=cmd_policy_get)

    policy_set = subparsers.add_parser("policy-set", help="Set network policy")
    policy_set.add_argument("policy", help="Policy JSON")
    policy_set.set_defaults(func=cmd_policy_set)

    # Checkpoint commands
    cp_list = subparsers.add_parser("checkpoint-list", help="List checkpoints")
    cp_list.set_defaults(func=cmd_checkpoint_list)

    cp_create = subparsers.add_parser("checkpoint-create", help="Create checkpoint")
    cp_create.add_argument("comment", nargs="?", help="Checkpoint comment")
    cp_create.set_defaults(func=cmd_checkpoint_create)

    cp_get = subparsers.add_parser("checkpoint-get", help="Get checkpoint details")
    cp_get.add_argument("id", help="Checkpoint ID")
    cp_get.set_defaults(func=cmd_checkpoint_get)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Check if sprite is required
    sprite_required = args.command.startswith("fs-") or args.command.startswith("policy-") or args.command.startswith("checkpoint-")
    if sprite_required and not args.sprite:
        print(f"Error: --sprite is required for {args.command}", file=sys.stderr)
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
