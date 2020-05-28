from io import BytesIO

import requests
from smalld import SmallD

smalld = SmallD()

CAT_API = "http://aws.random.cat/meow"


@smalld.on_message_create()
def on_message(msg):
    if msg.content == "++cat":
        cat_url = requests.get(CAT_API).json()["file"]
        cat_pic = requests.get(cat_url).content
        smalld.post(
            f"/channels/{msg.channel_id}/messages",
            payload={"content": "Enjoy your cat pic!"},
            attachments=[("cat.jpg", BytesIO(cat_pic), "image/jpeg")],
        )


smalld.run()
