# Example: List Services
# Endpoint: GET /v1/sprites/{name}/services

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

services = sprite.list_services()

result = []
for svc in services:
    item = {"name": svc.service.name, "cmd": svc.service.cmd}
    if svc.state:
        item["status"] = svc.state.status
    result.append(item)

print(json.dumps(result, indent=2))
