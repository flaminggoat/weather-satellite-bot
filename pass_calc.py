#!/usr/bin/env python3
from skyfield.api import load, wgs84
import urllib.request
import os
from datetime import datetime, timedelta
import asyncio

LAT = 51.751091415126346
LON = -1.2783613076759626

TLE_URL = 'https://celestrak.com/NORAD/elements/weather.txt'

SATELLITES = [
    ('NOAA 15', 'APT', "137.62M"),
    ('NOAA 18', 'APT', "137.9125M"),
    ('NOAA 19', 'APT', "137.1M"),
    ('METEOR-M 2', 'LRPT', '137.1M')
]

NOAA_APT_DIR = '$HOME/noaa-apt/'

TLE_DIR = os.path.dirname(__file__) + '/tle/'
RAW_DIR = os.path.dirname(__file__) + '/raw/'
IMG_DIR = os.path.dirname(__file__) + '/img/'

TLE_FILE = TLE_DIR + 'weather.txt'


def update_tles():
    urllib.request.urlretrieve(TLE_URL,TLE_FILE)

async def record_lrpt(file_name, sat, timestamp):
    try:
        # Record the pass to a wav file
        proc = await asyncio.create_subprocess_shell("timeout {} rtl_fm -M raw -f {} -s 140k -g 49.6 {}".format(
            sat['duration_seconds'], sat['sat'][2], RAW_DIR + file_name))
        await proc.communicate()
    except asyncio.CancelledError:
        proc.terminate()

async def record_noaa(file_name, sat, timestamp):
    try:
        # Record the pass to a wav file
        proc = await asyncio.create_subprocess_shell("timeout {} rtl_fm -f {} -Mfm -s 50k -g 49.6 -E deemp -F 9 | sox -r 50k -t s16 -L -c 1 - -t wav {}.wav".format(
            sat['duration_seconds'], sat['sat'][2], RAW_DIR + file_name))
        await proc.communicate()
    except asyncio.CancelledError:
        proc.terminate()

    try:
        # Decode the wav to an image
        print(timestamp)
        proc = await asyncio.create_subprocess_shell("(cd {}; ./noaa-apt -c telemetry -m yes -t {} -s {} -F -o {}.png {}.wav)".format(NOAA_APT_DIR, timestamp, sat['sat'][0].lower().replace(" ", "_"), IMG_DIR + file_name, RAW_DIR + file_name))
        await proc.communicate()
    except asyncio.CancelledError:
        proc.terminate()

    os.remove(RAW_DIR + file_name + '.wav')


async def pass_record_task(passes_queue: asyncio.Queue = None, image_queue: asyncio.Queue = None):
    while True:
        # obs = ephem.Observer()
        # obs.lat, obs.lon = LAT, LON
        # obs.date = ephem.now()
        # obs.horizon = "15"

        passes = []

        tles = load.tle_file(TLE_FILE)
        tle_by_name = {sat.name: sat for sat in tles}

        station = wgs84.latlon(LAT, LON)
        ts = load.timescale()
        t0 = ts.now()
        t1 = ts.utc(t0.utc_datetime() + timedelta(days=1))

        # Calculate the next pass for all satellites
        for sat in SATELLITES:
            satellite = tle_by_name[sat[0]]
            print(satellite)
            t, events = satellite.find_events(station,t0,t1, altitude_degrees=10)
            all_passes = [t[i:i + 3] for i in range(0, len(t), 3)]
            difference = satellite - station

            for pas in all_passes:
                if len(pas) < 3:
                    break

                peak_elevation = difference.at(pas[1]).altaz()[0].degrees
                if peak_elevation > 20:
                    # print(peak_elevation)
                    pass_start = pas[0].utc_datetime().timestamp()
                    pass_end = pas[2].utc_datetime().timestamp()
                    duration_seconds = (pass_end - pass_start)
                    # print(duration_seconds)
                    passes.append({"sat": sat, "start": pass_start, "duration_seconds": duration_seconds})

        # Find the satellite pass that is soonest
        passes.sort(key=lambda x: x["start"])
        sat = passes[0]
        # sat['start'] = t0.utc_datetime().timestamp()
        # sat['duration_seconds'] = 10
        print("{} time until pass: {} hours".format(
            sat['sat'][0], (sat['start'] - t0.utc_datetime().timestamp())/(60*60)))

        # Wait until the pass is starting
        await asyncio.sleep(sat['start'] - t0.utc_datetime().timestamp())

        file_name = "{}_{}_UTC".format(sat['sat'][0], datetime.utcnow())
        file_name = file_name.replace("/", "-").replace(":", "-").replace(" ", "_")

        print("{} pass starting. Duration {}s".format(
            file_name, sat['duration_seconds']))

        timestamp = datetime.utcnow().isoformat("T") + "-00:00"

        if sat['sat'][1] == 'APT':
            await record_noaa(file_name, sat, timestamp)
            if image_queue != None:
                await image_queue.put(IMG_DIR + file_name)
        elif sat['sat'][1] == 'LRPT':
            await record_lrpt(file_name, sat, timestamp)


