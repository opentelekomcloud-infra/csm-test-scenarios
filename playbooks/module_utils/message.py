#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc
import datetime
import json
import os
import socket

from ansible.module_utils.basic import AnsibleModule


def message_full_argument_spec(**kwargs):
    spec = dict(
        socket=dict(default=os.getenv("APIMON_PROFILER_MESSAGE_SOCKET", ""))
    )
    spec.update(kwargs)
    return spec


class MessageModule:
    """Openstack Module is a base class for all Message Module classes."""

    argument_spec = {}
    module_kwargs = {}

    def __init__(self):

        self.ansible = AnsibleModule(
            message_full_argument_spec(**self.argument_spec),
            **self.module_kwargs)
        self.params = self.ansible.params
        self.module_name = self.ansible._name
        self.results = {'changed': False}
        self.exit = self.exit_json = self.ansible.exit_json
        self.fail = self.fail_json = self.ansible.fail_json

    def log(self, msg):
        """Prints log message to system log.

        Arguments:
            msg {str} -- Log message
        """
        self.ansible.log(msg)

    def debug(self, msg):
        """Prints debug message to system log

        Arguments:
            msg {str} -- Debug message.
        """
        if self.ansible._debug or self.ansible._verbosity > 2:
            self.ansible.log(msg)

    @abc.abstractmethod
    def run(self):
        pass

    def __call__(self):
        """Execute `run` function when calling the instance.
        """

        try:
            results = self.run()
            if results and isinstance(results, dict):
                self.ansible.exit_json(**results)

        except Exception as e:
            self.ansible.fail_json(msg=str(e))

    @staticmethod
    def serialize(msg) -> str:
        """Serialize data as json string"""
        try:
            return json.dumps(msg, separators=(',', ':'))
        except json.JSONDecodeError as err:
            return err.msg

    @staticmethod
    def create_metric(name,
                      value,
                      environment: str = None,
                      zone: str = None, **kwargs):
        """
        Creates statsd type metric
        :param name: Metric name
        :param value: Gathered value
        :param environment:
        :param zone:
        :param kwargs:
        :return:
        """
        message = {
            'name': name,
            'value': value,
            'environment': environment,
            'zone': zone,
            'metric_type': kwargs.get('metric_type', 'ms'),
            'az': kwargs.get('az', 'default'),
            'timestamp': kwargs.get('timestamp', datetime.datetime.now().isoformat()),
            '__type': kwargs.get('__type', 'metric')
        }

        return message

    def push_metric(self, data, message_socket_address):
        """push metrics to socket"""
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as _socket:
            try:
                _socket.connect(message_socket_address)
                msg = '%s\n' % self.serialize(data)
                _socket.sendall(msg.encode('utf8'))
            except socket.error as err:
                self.ansible.fail_json(msg='error establishing connection to socket')
                raise err
            except Exception as ex:
                self.ansible.fail_json(msg='error writing message to socket')
                raise ex
