# Example: Quick Start
# Endpoint: quickstart

# step: Install
# pip install sprites-py

# step: Setup client
import os
from sprites import SpritesClient
client = SpritesClient(os.environ["SPRITE_TOKEN"])

# step: Create a sprite
client.create_sprite(os.environ["SPRITE_NAME"])

# step: Run Python
output = client.sprite(os.environ["SPRITE_NAME"]).command("python", "-c", "print(2+2)", timeout=30).output()
print(output.decode(), end="")

# step: Clean up
client.delete_sprite(os.environ["SPRITE_NAME"])
