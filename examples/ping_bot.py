import logging

from smalld import SmallD

logging.basicConfig(level=logging.INFO)

smalld = SmallD()


@smalld.on_message_create()
def on_message(msg):
    if msg.content == "++ping":
        smalld.post(f"/channels/{msg.channel_id}/messages", {"content": "pong"})


smalld.run()
