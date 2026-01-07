# Example: Set Network Policy
# Endpoint: POST /v1/sprites/{name}/policy/network

import os

from sprites import NetworkPolicy, PolicyRule, SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

policy = NetworkPolicy(
    rules=[
        PolicyRule(domain="api.github.com", action="allow"),
        PolicyRule(domain="*.npmjs.org", action="allow"),
    ]
)

sprite.update_network_policy(policy)

print("Network policy updated")
