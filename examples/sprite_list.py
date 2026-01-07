# Example: List Sprites
# Endpoint: GET /v1/sprites

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]

client = SpritesClient(token)

sprites = client.list_sprites()

result = []
for s in sprites:
    item = {"name": s.name}
    if s.id:
        item["id"] = s.id
    if s.status:
        item["status"] = s.status
    if s.url:
        item["url"] = s.url
    result.append(item)

print(json.dumps(result, indent=2))
