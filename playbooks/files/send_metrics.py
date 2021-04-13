#!/usr/bin/env python3

import json
import os
import socket
import sys


def emit_metric(socket_name, serialized_metric):
    print(serialized_metric, file=sys.stdout)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as _socket:
        _socket.connect(socket_name)
        msg = f'{serialized_metric}\n'
        _socket.sendall(msg.encode('utf8'))


def main():
    socket = os.getenv('APIMON_PROFILER_MESSAGE_SOCKET')
    serialized_metric = json.loads(sys.argv[1].replace("\'", "\""))
    for metric in serialized_metric:
        emit_metric(socket, metric)


main()
