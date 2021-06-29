#!/usr/bin/env python3
import telepot
import os
import asyncio
import pass_calc
import sys

BOT_KEY = ''
CHAT_ID = ''

async def post_photo_to_telegram(image_queue):
    bot = telepot.Bot(BOT_KEY)
    while True:
        image_path = await image_queue.get()
        print("sending photo to telegram:" + image_path)
        with open(image_path + '.png', "rb") as photo:
            for i in range(3):
                try:
                    # bot.sendMessage(CHAT_ID, image_path.split('/')[-1])
                    bot.sendPhoto(CHAT_ID, photo, caption=image_path.split('/')[-1])
                    break
                except:
                    print("Failed to send telegram message on attempt: {}".format(i))
                    pass

if __name__ == "__main__":
    BOT_KEY = sys.argv[1]
    CHAT_ID = sys.argv[2]

    loop = asyncio.get_event_loop()

    pass_calc.update_tles()

    image_queue = asyncio.Queue(10)
    loop.create_task(pass_calc.pass_record_task(image_queue=image_queue))
    loop.create_task(post_photo_to_telegram(image_queue))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    loop.close()
