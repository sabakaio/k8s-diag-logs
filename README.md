# Kubernetes diagnostic logs

It should be run on Kubernetes cluster with InfluxDB. 
The script goes over a list of *nodes* and a list of *pods*, get stats for mesurements 
(`cpu/usage_rate` and `memory/usage` by default) for 15 minues (by default) time frame and write data in *stdout* in *json* format.
