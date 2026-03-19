# Example: Create Service
# Endpoint: PUT /v1/sprites/{name}/services/{service_name}

import json
import os

from sprites import SpritesClient
from sprites.services import create_service

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]
service_name = os.environ["SERVICE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

stream = create_service(
    sprite,
    name=service_name,
    cmd="python",
    args=["-m", "http.server", "8000"],
    http_port=8000,
)

for event in stream:
    print(json.dumps({"type": event.type, "timestamp": event.timestamp}))
