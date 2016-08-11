#!/usr/bin/env python3
from influxdb import InfluxDBClient

client = InfluxDBClient.from_DSN('influxdb://localhost:8086/k8s', timeout=5)
res = client.query('SELECT sum("value") FROM "cpu/usage_rate" WHERE "type" = \'node\' AND time > now() - 15m GROUP BY time(1m)')
print(res)
