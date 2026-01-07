# Example: Get Sprite
# Endpoint: GET /v1/sprites/{name}

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)

sprite = client.get_sprite(sprite_name)

result = {"name": sprite.name}
if sprite.info:
    if sprite.info.id:
        result["id"] = sprite.info.id
    if sprite.info.status:
        result["status"] = sprite.info.status
    if sprite.info.url:
        result["url"] = sprite.info.url

print(json.dumps(result, indent=2))
