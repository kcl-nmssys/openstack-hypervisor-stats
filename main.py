#!/usr/bin/python
#
# Store OpenStack hypervisor statistics in InfluxDB
# Xand Meaden, King's College London

import datetime
import influxdb
from novaclient import client
import os
import sys
import yaml

settings = [
    'OS_API_VER', 'OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_NAME', 'OS_AUTH_URL',
    'INFLUX_HOST', 'INFLUX_PORT', 'INFLUX_USERNAME', 'INFLUX_PASSWORD', 'INFLUX_DB'
]

for setting in settings:
    if setting not in os.environ:
        print('Missing environment variable %s\n' % setting)
        sys.exit(1)

try:
    with client.Client(os.environ['OS_API_VER'], os.environ['OS_USERNAME'], os.environ['OS_PASSWORD'], os.environ['OS_TENANT_NAME'], os.environ['OS_AUTH_URL']) as nova:
        hypervisors = nova.hypervisors.list(detailed=True)
except Exception as e:
    sys.stderr.write('Failed getting hypervisor details: %s\n' % e)
    sys.exit(1)

now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

metrics = {}
metrics['vcpus'] = {}
metrics['vcpus']['TOTAL'] = 0
metrics['vcpus_used'] = {}
metrics['vcpus_used']['TOTAL'] = 0
metrics['memory_mb'] = {}
metrics['memory_mb']['TOTAL'] = 0
metrics['memory_mb_used'] = {}
metrics['memory_mb_used']['TOTAL'] = 0
metrics['running_vms'] = {}
metrics['running_vms']['TOTAL'] = 0
metrics['state'] = {}
metrics['status'] = {}

for hypervisor in hypervisors:
    hostname = hypervisor.hypervisor_hostname.encode('ascii').split('.')[0]
    metrics['vcpus'][hostname] = hypervisor.vcpus
    metrics['vcpus']['TOTAL'] += hypervisor.vcpus

    metrics['vcpus_used'][hostname] = hypervisor.vcpus_used
    metrics['vcpus_used']['TOTAL'] += hypervisor.vcpus_used

    metrics['memory_mb'][hostname] = hypervisor.memory_mb
    metrics['memory_mb']['TOTAL'] += hypervisor.memory_mb

    metrics['memory_mb_used'][hostname] = hypervisor.memory_mb_used
    metrics['memory_mb_used']['TOTAL'] += hypervisor.memory_mb_used

    metrics['running_vms'][hostname] = hypervisor.running_vms
    metrics['running_vms']['TOTAL'] += hypervisor.running_vms

    state = hypervisor.state.encode('ascii')
    status = hypervisor.status.encode('ascii')

    if state in metrics['state']:
        metrics['state'][state] += 1
    else:
        metrics['state'][state] = 1

    if status in metrics['status']:
        metrics['status'][status] += 1
    else:
        metrics['status'][status] = 1

payload = []
for reading in metrics.keys():
    for item in metrics[reading]:
        payload.append({'measurement': reading, 'time': now, 'fields': {reading: float(metrics[reading][item])}, 'tags': {'item': item}})

try:
    influx = influxdb.InfluxDBClient(host=os.environ['INFLUX_HOST'], port=os.environ['INFLUX_PORT'], username=os.environ['INFLUX_USERNAME'], password=os.environ['INFLUX_PASSWORD'], ssl=True, verify_ssl=True)
    influx.write_points(payload, database=os.environ['INFLUX_DB'])
except Exception as e:
    sys.stderr.write('Failed writing data to InfluxDB: %s\n' % e)
    sys.exit(1)
