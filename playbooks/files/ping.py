#!/usr/bin/env python3

import json
import re
import socket
import subprocess as sp
import sys


def serialize_metric(msg):
    try:
        return json.dumps(msg, separators=(',', ':'))
    except json.JSONDecodeError as err:
        return err.msg


def emit_metric(host, port, metric):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _socket:
        _socket.connect((host, int(port)))
        msg = f'{serialize_metric(metric)}\n'
        _socket.sendall(msg.encode('utf8'))


def main():
    host = sys.argv[2]
    metric_name = f'{sys.argv[1]}.{sys.argv[3]}'
    if len(sys.argv) == 5:
        request_timeout = int(sys.argv[4])
    else:
        request_timeout = 5
    graphite_host = sys.argv[5]
    graphite_port = sys.argv[6]
    if len(sys.argv) == 8:
        packet_size = sys.argv[7]
    else:
        packet_size = '56'
    duration = -1
    try:
        rsp = sp.check_output(
            ['ping', '-c', '1', '-s', packet_size, host],
            stderr=sp.STDOUT,
            universal_newlines=True
        )
        duration = re.search(r'time=(\d+)', rsp).group(1)
        metric_name = f'{metric_name}.success'
        metric = dict(
            name=metric_name,
            value=duration,
            metric_type='ms',
            __type='metric'
        )
        rc = 0
    except AttributeError as ae:
        metric = dict(
            name=f'{metric_name}.failed',
            metric_type='c',
            __type='metric'
        )
        rc = 3
        print(f'{host} caused {ae} by invalid response')

    emit_metric(graphite_host, graphite_port, metric)
    exit(rc)


main()
