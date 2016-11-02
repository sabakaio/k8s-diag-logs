#!/usr/bin/env python3
import argparse
import asyncio
import json
import itertools

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import config, Csv
from influxdb import InfluxDBClient

# suppress self-signed certificate warnings
requests.packages.urllib3.disable_warnings()

output_format = config('OUTPUT_FORMAT', '')

parser = argparse.ArgumentParser(description='Kubernetes metrics dumper')
parser.add_argument('--schedule', action='store_true',
                    help='Schedule periodic metrics dumb based on METRICS_FRAME env variable')
parser.add_argument('--format', default=output_format, help='Output format (see `str.format` doc)')


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

assoc = {"node": "nodename", "pod": "pod_name"}


def k_get(k_type):
    url = kube_api.strip('/') + '/api/v1/' + k_type.strip('/') + 's'
    headers = {}
    if kube_token:
        headers['Authorization'] = 'Bearer ' + kube_token
    res = requests.get(url, headers=headers, verify=False)
    res.raise_for_status()
    return [item['metadata']['name'] for item in res.json()['items']]


def metrics(k_type):
    for name in k_get(k_type):
        for m in measurements:
            res = client.query('''
                SELECT MEAN("value"), PERCENTILE("value", 90)
                FROM "%s"
                WHERE "type" = \'%s\'
                AND %s = \'%s\'
                AND time > now() - %dm GROUP BY time(1m)
                ''' % (m, k_type, assoc[k_type], name, time_frame))
            for r in itertools.chain(*res):
                r.update(measurement=m, type=k_type, name=name)
                yield r


def dump(fmt):
    for r in itertools.chain(metrics('node'), metrics('pod')):
        if fmt:
            print(fmt.format(**r))
        else:
            print(json.dumps(r))


if __name__ == '__main__':
    args = parser.parse_args()
    dump_kwargs = {'fmt': args.format}
    # Show metrics immideately
    dump(**dump_kwargs)
    # Schedule text calls
    if args.schedule:
        scheduler = AsyncIOScheduler({'apscheduler.timezone': 'UTC'})
        scheduler.add_job(dump, 'interval', minutes=time_frame, kwargs=dump_kwargs)
        scheduler.start()

        # Execution will block here until Ctrl+C is pressed.
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            pass
