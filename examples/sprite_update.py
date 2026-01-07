# Example: Update Sprite
# Endpoint: PUT /v1/sprites/{name}

import os

from sprites import SpritesClient, URLSettings

token = os.environ["SPRITE_TOKEN"]
sprite_name = os.environ["SPRITE_NAME"]

client = SpritesClient(token)

client.update_url_settings(sprite_name, URLSettings(auth="public"))

print("URL settings updated")
