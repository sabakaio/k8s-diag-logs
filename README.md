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
