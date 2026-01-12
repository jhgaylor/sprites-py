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
if sprite.id:
    result["id"] = sprite.id
if sprite.status:
    result["status"] = sprite.status
if sprite.url:
    result["url"] = sprite.url

print(json.dumps(result, indent=2))
