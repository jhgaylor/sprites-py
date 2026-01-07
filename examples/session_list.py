# Example: List Sessions
# Endpoint: GET /v1/sprites/{name}/exec

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

sessions = sprite.list_sessions()

result = []
for s in sessions:
    item = {
        "id": s.id,
        "command": s.command,
        "is_active": s.is_active,
        "tty": s.tty,
    }
    result.append(item)

print(json.dumps(result, indent=2))
