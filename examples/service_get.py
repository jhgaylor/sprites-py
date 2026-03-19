# Example: Get Service
# Endpoint: GET /v1/sprites/{name}/services/{service_name}

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]
service_name = os.environ["SERVICE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

svc = sprite.get_service(service_name)

result = {"name": svc.service.name, "cmd": svc.service.cmd}
if svc.state:
    result["status"] = svc.state.status

print(json.dumps(result, indent=2))
