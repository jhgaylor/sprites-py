# Example: Execute Command
# Endpoint: WSS /v1/sprites/{name}/exec

import os
import sys

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

# Start a command that runs for 30s (TTY sessions stay alive after disconnect)
cmd = sprite.command(
    "python", "-c",
    "import time; print('Server ready on port 8080', flush=True); time.sleep(30)"
)
cmd.tty = True  # TTY sessions are detachable
cmd.stdout = sys.stdout.buffer  # Stream output directly
cmd.timeout = 2  # Disconnect after 2 seconds (session keeps running)

try:
    cmd.run()
except Exception:
    pass  # Timeout is expected - we disconnect while session continues
