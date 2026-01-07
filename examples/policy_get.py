# Example: Get Network Policy
# Endpoint: GET /v1/sprites/{name}/policy/network

import json
import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

policy = sprite.get_network_policy()

result = {
    "rules": [
        {"domain": rule.domain, "action": rule.action}
        for rule in policy.rules
    ]
}

print(json.dumps(result, indent=2))
