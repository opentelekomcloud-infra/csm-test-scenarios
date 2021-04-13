#!/usr/bin/env python3

import json
import re
import subprocess as sp
import sys
from argparse import ArgumentParser


def serialize_metric(msg):
    try:
        return json.dumps(msg, separators=(',', ':'))
    except json.JSONDecodeError as err:
        return err.msg


def main():
    arg_p = ArgumentParser(prog='Ping module', description='Script for pinging selected hosts')
    arg_p.add_argument('--metric_name', default='csm_test_metric')
    arg_p.add_argument('--hosts', default=[])
    arg_p.add_argument('--packet_size', default='56')
    args = arg_p.parse_args()

    rc = 0
    metrics = []

    hosts = json.loads(args.hosts.replace("\'", "\""))
    for host in hosts:
        metric_name = f'{args.metric_name}.{host["name"]}'
        duration = -1
        try:
            rsp = sp.check_output(
                ['ping', '-c', '1', '-s', args.packet_size, host["ip"]],
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
            print(f'{host["name"]} caused {ae} by invalid response')

        serialied_metric = serialize_metric(metric)
        metrics.append(serialied_metric)
    print(metrics, file=sys.stdout)
    exit(rc)


main()
