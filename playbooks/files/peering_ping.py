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
        msg = '%s\n' % serialize_metric(metric)
        _socket.sendall(msg.encode('utf8'))


def main():
    host = sys.argv[1]
    metric_name = 'csm_peering_ping.%s' % sys.argv[2]
    if len(sys.argv) == 4:
        request_timeout = int(sys.argv[3])
    else:
        request_timeout = 5
    graphite_host = sys.argv[4]
    graphite_port = sys.argv[5]
    duration = -1
    try:
        rsp = sp.check_output(
            ['ping', '-c', '1', host],
            stderr=sp.STDOUT,
            universal_newlines=True
        )
        duration = re.search(r'time=(\d+)', rsp).group(1)
        metric_name = '%s.success' % metric_name
        metric = dict(
            name=metric_name,
            value=duration,
            metric_type='ms',
            __type='metric'
        )
        rc = 0
    except AttributeError as ae:
        metric = dict(
            name='%s.failed' % metric_name,
            metric_type='c',
            __type='metric'
        )
        rc = 3
        print('%s caused %s by invalid response' % (host, ae))

    emit_metric(graphite_host, graphite_port, metric)

    exit(rc)


main()
