# Example: Start Service
# Endpoint: POST /v1/sprites/{name}/services/{service_name}/start

import json
import os

from sprites import SpritesClient
from sprites.services import start_service

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]
service_name = os.environ["SERVICE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

stream = start_service(sprite, name=service_name)

for event in stream:
    print(json.dumps({"type": event.type, "timestamp": event.timestamp}))
