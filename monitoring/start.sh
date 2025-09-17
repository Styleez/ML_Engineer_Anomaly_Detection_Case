#!/bin/sh

# Start Prometheus in background
/bin/prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus &

# Start Grafana
/run.sh
