# Example: Get Checkpoint
# Endpoint: GET /v1/sprites/{name}/checkpoints/{checkpoint_id}

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]
checkpoint_id = os.environ.get("CHECKPOINT_ID", "v1")

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

checkpoint = sprite.get_checkpoint(checkpoint_id)

result = {
    "id": checkpoint.id,
    "create_time": checkpoint.create_time.isoformat().replace("+00:00", "Z"),
}
if checkpoint.comment:
    result["comment"] = checkpoint.comment

print(json.dumps(result, indent=2))
