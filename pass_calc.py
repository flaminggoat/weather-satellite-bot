#!/usr/bin/env python3
import ephem
import urllib.request
import os
from datetime import datetime
import asyncio

LAT = '51.751091415126346'
LON = '-1.2783613076759626'

NOAA_TLES = [
    ('noaa_15', 'https://service.eumetsat.int/tle/data_out/latest_n15_tle.txt', "137.62M"),
    ('noaa_18', 'https://service.eumetsat.int/tle/data_out/latest_n18_tle.txt', "137.9125M"),
    ('noaa_19', 'https://service.eumetsat.int/tle/data_out/latest_n19_tle.txt', "137.1M"),
]

TLE_DIR = os.path.dirname(__file__) + '/tle/'
RAW_DIR = os.path.dirname(__file__) + '/raw/'
IMG_DIR = os.path.dirname(__file__) + '/img/'


def update_tles():
    for sat in NOAA_TLES:
        try:
            urllib.request.urlretrieve(sat[1], TLE_DIR + sat[0])
        except:
            print("ERROR retrieving TLE: " + [sat[0]])


async def pass_record_task(passes_queue: asyncio.Queue = None, image_queue: asyncio.Queue = None):
    while True:
        obs = ephem.Observer()
        obs.lat, obs.lon = LAT, LON
        obs.date = ephem.now()
        obs.horizon = "15"

        passes = []

        # Calculate the next pass for all satellites
        for sat in NOAA_TLES:
            with open(TLE_DIR + sat[0], 'r') as tle:
                s = tle.readline()
                t = tle.readline()
                satellite = ephem.readtle(sat[0], s, t)
                satellite.compute(obs)
                sat_pass = obs.next_pass(satellite)
                pass_start = sat_pass[0]
                pass_end = sat_pass[4]
                duration_seconds = (pass_end - pass_start)*24*60*60 + 120
                passes.append({"name": sat[0], "start": pass_start,
                               "freq": sat[2], "duration_seconds": duration_seconds})
                if passes_queue != None:
                    await passes_queue.put((sat[0], "{} UTC".format(pass_start)))

        # Find the satellite pass that is soonest
        passes.sort(key=lambda x: x["start"])
        sat = passes[0]
        # sat['start'] = ephem.now()
        # sat['duration_seconds'] = 10
        print("{} time until pass: {} hours".format(
            sat['name'], (sat['start'] - ephem.now())*24))

        # Wait until the pass is starting
        await asyncio.sleep((sat['start'] - ephem.now()) * 24 * 60 * 60 - 60)

        file_name = "{}_{}_UTC".format(sat['name'], sat["start"])
        file_name = file_name.replace(
            "/", "-").replace(":", "-").replace(" ", "_")

        print("{} pass starting. Duration {}s".format(
            file_name, sat['duration_seconds']))

        timestamp = datetime.utcnow().isoformat("T") + "-00:00"

        try:
            # Record the pass to a wav file
            proc = await asyncio.create_subprocess_shell("timeout {} rtl_fm -f {} -Mfm -s 60k -g 49.6 -E deemp -F 9 | sox -r 60k -t s16 -L -c 1 - -t wav {}.wav".format(
                sat['duration_seconds'], sat['freq'], RAW_DIR + file_name))
            await proc.communicate()
        except asyncio.CancelledError:
            proc.terminate()

        try:
            # Decode the wav to an image
            print(timestamp)
            proc = await asyncio.create_subprocess_shell("noaa-apt -c telemetry -m yes -t {} -s {} -F -o {}.png {}.wav".format(timestamp, sat['name'], IMG_DIR + file_name, RAW_DIR + file_name))
            await proc.communicate()
        except asyncio.CancelledError:
            proc.terminate()

        # os.remove(RAW_DIR + file_name + '.wav')

        if image_queue != None:
            await image_queue.put(IMG_DIR + file_name)
