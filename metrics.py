#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import itertools

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import config, Csv
from influxdb import InfluxDBClient


parser = argparse.ArgumentParser(description='Kubernetes metrics dumper')
parser.add_argument('--schedule', action='store_true',
                    help='Schedule periodic metrics dumb based on METRICS_FRAME env variable')


# KUBERNETES SETTINGS

kube_api = config('KUBE_API', 'http://localhost:8001')
kube_token_file = config('KUBE_TOKEN_FILE', '')
kube_token = config('KUBE_TOKEN', '')

if not kube_token and kube_token_file:
    with open(kube_token_file) as f:
        kube_token = f.read()


# INFLUXDB SETTINGS

influxdb_dsn = config('INFLUXDB_DSN', 'influxdb://localhost:8086/k8s')
measurements = config('MEASUREMENTS', 'cpu/usage_rate,memory/usage', cast=Csv())
time_frame = config('METRICS_FRAME', 15, cast=int)  # in minutes

client = InfluxDBClient.from_DSN(influxdb_dsn, timeout=5)


# APPLICATION

def k_get(k_type):
    url = kube_api.strip('/') + '/api/v1/' + k_type.strip('/') + 's'
    headers = {}
    if kube_token:
        headers['Authorization'] = 'Bearer ' + kube_token
    res = requests.get(url)
    res.raise_for_status()
    return [item['metadata']['name'] for item in res.json()['items']]


def metrics(k_type):
    for name in k_get(k_type):
        for m in measurements:
            res = client.query('''
                SELECT MEAN("value"), MAX("value")
                FROM "%s"
                WHERE "type" = \'%s\'
                AND time > now() - %dm GROUP BY time(%s)
                ''' % (m, k_type, time_frame, '1m'))
            for r in itertools.chain(*res):
                r.update(type=k_type, name=name)
                yield r


def dump():
    for r in itertools.chain(metrics('node'), metrics('pod')):
        print(json.dumps(r))


if __name__ == '__main__':
    args = parser.parse_args()
    # Show metrics immideately
    dump()
    # Schedule text calls
    if args.schedule:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(dump, 'interval', minutes=time_frame)
        scheduler.start()

        # Execution will block here until Ctrl+C is pressed.
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            pass
