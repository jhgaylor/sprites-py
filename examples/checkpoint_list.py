# Example: List Checkpoints
# Endpoint: GET /v1/sprites/{name}/checkpoints

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

checkpoints = sprite.list_checkpoints()

result = []
for cp in checkpoints:
    item = {"id": cp.id, "create_time": cp.create_time.isoformat().replace("+00:00", "Z")}
    if cp.comment:
        item["comment"] = cp.comment
    result.append(item)

print(json.dumps(result, indent=2))
