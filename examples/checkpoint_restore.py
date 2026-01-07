# Example: Restore Checkpoint
# Endpoint: POST /v1/sprites/{name}/checkpoints/{checkpoint_id}/restore

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]
checkpoint_id = os.environ.get("CHECKPOINT_ID", "v1")

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

stream = sprite.restore_checkpoint(checkpoint_id)

for msg in stream:
    print(json.dumps({"type": msg.type, "data": msg.data}))
