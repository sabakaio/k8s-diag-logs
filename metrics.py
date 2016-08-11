#!/usr/bin/env python3
import itertools
import requests
from influxdb import InfluxDBClient

client = InfluxDBClient.from_DSN('influxdb://localhost:8086/k8s', timeout=5)
measurements = ['cpu/usage_rate', 'memory/usage']

kubernetes_api = 'http://127.0.0.1:8001'

def k_get(k_type):
    url = kubernetes_api.strip('/') + '/api/v1/' + k_type.strip('/') + 's'
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
                AND time > now() - %s GROUP BY time(%s)
                ''' % (m, k_type, '15m', '1m'))
            for r in itertools.chain(*res):
                r.update(type=k_type, name=name)
                yield r

for r in itertools.chain(metrics('node'), metrics('pod')):
    print(r)
