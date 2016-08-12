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

assoc = {"node": "nodename", "pod": "pod_name" }
items = {}

def k_get(k_type):
    url = kube_api.strip('/') + '/api/v1/' + k_type.strip('/') + 's'
    headers = {}
    if kube_token:
        headers['Authorization'] = 'Bearer ' + kube_token
    res = requests.get(url)
    res.raise_for_status()
    return res.json()['items']

def k_get_names(k_type):
    return [item['metadata']['name'] for item in items[k_type]]

def k_get_limit(k_type, k_inst):
    if k_type == "node":
        for item in items[k_type]:
            if item['metadata']['name'] == k_inst:
                return convert_to_byte(item['status']['capacity']['memory'])
    if k_type == "pod":
        for item in items[k_type]:
            if item['metadata']['name'] == k_inst:
                limits_sum = 0
                for c in item['spec']['containers']:
                    if ('resources' in c) and \
                        ('limits' in c['resources']) and \
                        ('memory' in c['resources']['limits']):
                            limits_sum += convert_to_byte(c['resources']['limits']['memory'])
                    else:
                        limits_sum = 0
                        break
                if limits_sum > 0:
                    return limits_sum
                else:
                    return(k_get_limit('node', item['spec']['nodeName']))

bi_in_bytes = {
        'Ki': 1024,
        'Mi': 1024*1024,
        'Gi': 1024*1024*1024
        }

def convert_to_byte(BiBy):
    suf = BiBy[-2:]
    if (suf) in bi_in_bytes:
        return int(BiBy.strip(suf)) * bi_in_bytes[suf]
    else:
        return BiBy

def metrics(k_type):
    for name in k_get_names(k_type):
        for m in measurements:
            res = client.query('''
                SELECT MEAN("value"), PERCENTILE("value", 90)
                FROM "%s"
                WHERE "type" = \'%s\'
                AND %s = \'%s\'
                AND time > now() - %dm GROUP BY time(%dm)
                ''' % (m, k_type, assoc[k_type], name, time_frame, time_frame))
            for r in itertools.chain(*res):
                if r.get("mean") and r.get("percentile"):
                    r.update(measurement=m, type=k_type, name=name)
                    if m == "memory/usage":
                        r.update(measurement="memory/usage_rate")
                        limit = k_get_limit(k_type, name)
                        r.update(mean=round(r.get("mean")*100/limit, 2),
                            percentile=round(r.get("percentile")*100/limit, 2))
                    r.update(mean=round(r.get("mean"),2),
                        percentile=round(r.get("percentile"),2))
                    yield r
                break


def dump():
    items['node'] = k_get('node')
    items['pod'] = k_get('pod')
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
