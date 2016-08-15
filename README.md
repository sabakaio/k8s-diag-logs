# Kubernetes diagnostic logs

It should be run on *Kubernetes* cluster with *InfluxDB*, e.g. on [ansible-kube](https://github.com/sabakaio/ansible-kube) setup.
The script goes over a list of *nodes* and a list of *pods*, get stats for mesurements
(`cpu/usage_rate` and `memory/usage` by default) for 15 minues (by default) time frame and write data in *stdout* in *json* format.

## Requirements

- The script is written in `Python 3`
- All required python packages are listed in the `requirements.txt` file
- Script should have access to *Kubernetes API*
- Script should have access to *InfluxDB API*

## Usage

These is the only one script `./metrics.py`. It dumps all diagnostic logs to *stdout*. To run it in a scheduled loop (e.g. dump every 15 minutes) pass `--schedule` option.

## Configuration

All configuration could be made with environment variables

### General

- `OUTPUT_FORMAT` output format, e.g. `{time}|{type}|{name}|{measurement}|{mean}|{percentile}`. Could be also set using `--format` option. Default output is `JSON` encoded data.

### Kubernetes

- `KUBE_API` Kubernetes API address (default is `http://localhost:8001`,available with `kubectl proxy`)
- `KUBE_TOKEN_FILE` is file name where auth token was placed in case of [accessing the API from a Pod](http://kubernetes.io/docs/user-guide/accessing-the-cluster/#accessing-the-api-from-a-pod)
- `KUBE_TOKEN` if you want to pass auth token manually

### InfluxDB

- `INFLUXDB_DSN` InfluxDB API address (default is `influxdb://localhost:8086/k8s`)
- `MEASUREMENTS` comma-separated measurements list to dump (default is `cpu/usage_rate,memory/usage`)
- `METRICS_FRAME` a time frame to query data (deault is `15` minutes)
