# Example: Create Checkpoint
# Endpoint: POST /v1/sprites/{name}/checkpoint

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

stream = sprite.create_checkpoint("my-checkpoint")

for msg in stream:
    print(json.dumps({"type": msg.type, "data": msg.data}))
