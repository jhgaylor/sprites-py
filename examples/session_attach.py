# Example: Attach to Session
# Endpoint: WSS /v1/sprites/{name}/exec/{session_id}

import os
import sys

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

# Find the session from exec example
sessions = sprite.list_sessions()
target_session = None
for s in sessions:
    if "time.sleep" in s.command or "python" in s.command:
        target_session = s
        break

if not target_session:
    print("No running session found")
    sys.exit(1)

print(f"Attaching to session {target_session.id}...")

# Attach and read buffered output (includes data from before we connected)
cmd = sprite.attach_session(target_session.id)
cmd.stdout = sys.stdout.buffer
cmd.timeout = 2

try:
    cmd.run()
except Exception:
    pass  # Timeout is expected
