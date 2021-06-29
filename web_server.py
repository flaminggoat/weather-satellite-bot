#!/usr/bin/env python3
from sanic import Sanic
from sanic.response import json, html
from jinja2 import Environment, FileSystemLoader
import os
from glob import glob
import asyncio
from itertools import tee
import pass_calc

env = Environment(loader=FileSystemLoader('./html'))
app = Sanic(__name__)

app.static('/img', './img')
app.static('/', './html')

next_pass = {}


@app.route('/')
async def test(request):
    images = glob(r'./img/*')
    images.sort(key=os.path.getmtime)
    images = list(map(lambda path: path[1:], images[-4:]))
    template = env.get_template('index.html')
    html_content = template.render(images=images, next_pass=next_pass)
    return html(html_content)


async def update_pass_dict_task(passes_queue):
    global next_pass
    while True:
        sat_pass = await passes_queue.get()
        next_pass[sat_pass[0]] = sat_pass[1]

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    pass_calc.update_tles()

    passes_queue = asyncio.Queue(10)
    loop.create_task(pass_calc.pass_record_task(passes_queue))
    loop.create_task(update_pass_dict_task(passes_queue))

    sanic_coro = app.create_server(
        host="0.0.0.0", port=8000, return_asyncio_server=True)
    loop.create_task(sanic_coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    loop.close()
