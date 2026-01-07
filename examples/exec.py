# Example: Execute Command
# Endpoint: WSS /v1/sprites/{name}/exec

import os

from sprites import SpritesClient

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)
sprite = client.sprite(sprite_name)

cmd = sprite.command("echo", "hello", "world")
output = cmd.output()

print(output.decode(), end="")
