import logging

from smalld import SmallD

smalld = SmallD.v8()

logging.basicConfig(level=logging.DEBUG)


@smalld.on_message_create
def on_message(msg):
    if msg.content == "++ping":
        smalld.post(f"/channels/{msg.channel_id}/messages", {"content": "pong"})


smalld.run()
