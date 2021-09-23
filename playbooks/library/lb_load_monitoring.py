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
import re

import requests
from ansible.module_utils.message import MessageModule

DOCUMENTATION = '''
---
module: lb_load_monitoring
short_description: Load balancer response times.
version_added: "1.0.0"
author: "Anton Sidelnikov (@anton-sidelnikov)"
description:
  - Get metrics from load balancer hosts and push it to unix socket server
  - APIMON_PROFILER_MESSAGE_SOCKET environment variable should be set.
options:
  target_address:
    description: IP address of target load balancer.
    type: str
    required: true
  timeout:
    description: Request timeout value.
    type: int
    default: 20
  protocol:
    description: Load balancer protocol.
    type: str
    default: http
  protocol_port:
    description: Load balancer listener port.
    type: int
    default: 80
  request_count:
    description: Count of requests.
    type: int
    default: 30
  interface:
    description: Public or internal address.
    type: str
    default: public
    choices=['public', 'internal']
  listener_type:
    description: Type of the listener to be checked.
    type: str
    default: http
    choices=['http', 'https', 'tcp']
requirements: []
'''

RETURN = '''
pushed_metrics:
  description: List of metrics to be pushed into socket
  type: complex
  returned: On Success
  contains:
    name:
      description: Name of metric.
      type: str
      sample: "mname"
    environment:
      description: From which environment run.
      type: str
      sample: "production_eu-de"
    zone:
      description: In which zone loadbalancer is deployed.
      type: str
      sample: "production_eu-de"
    timestamp:
      description: Current timestamp.
      type: str
      sample: "2021-02-15T08:57:23.701273"
    metric_type:
      description: Type of gathered value ('ms' for milliseconds).
      type: str
      sample: "ms"
    value:
      description: Response time in milliseconds
      type: int
      sample: 7
    az:
      description: AZ of responded server
      type: str
      sample: "eu-de-02"
    __type:
      description: Message type('metric' is default value).
      type: str
      sample: "metric"
'''

EXAMPLES = '''
# Get list of floating IPs statuses (all parameters are specified)
- lb_load_monitoring:
    lb_ip: "80.158.53.138"
  register: out
'''

SUCCESS_METRIC = 'csm_lb_timings'
TIMEOUT_METRIC = 'csm_lb_timeout'


class LbLoadMonitoring(MessageModule):
    argument_spec = dict(
        target_address=dict(type='str', required=True),
        timeout=dict(type='int', default=20),
        protocol=dict(type='str', default='http'),
        request_count=dict(type='int', default=30),
        protocol_port=dict(type='int', default=80),
        interface=dict(type='str', default='public', choices=['public', 'internal']),
        listener_type=dict(type='str', default='http', choices=['http', 'https', 'tcp'])
    )

    def run(self):
        metrics = []
        verify = True
        timeout = self.params['timeout']
        interface = self.params['interface']
        listener_type = self.params['listener_type']
        address = f"{self.params['protocol']}://{self.params['target_address']}" \
                  f":{self.params['protocol_port']}"
        if self.params['protocol'] == 'https':
            verify = False
        for _ in range(self.params['request_count']):
            try:
                res = requests.get(
                    address, headers={'Connection': 'close'}, verify=verify, timeout=timeout
                )
                metrics.append(self.create_metric(
                    name=f'{SUCCESS_METRIC}.{interface}.{listener_type}',
                    value=int(res.elapsed.total_seconds() * 1000),
                    metric_type='ms',
                    az=re.search(r'eu-de-\d+', res.headers['Backend-Server']).group()
                ))
            except requests.Timeout:
                self.log('timeout sending request to LB')
                metrics.append(self.create_metric(
                    name=f'{TIMEOUT_METRIC}.{interface}.{listener_type}.failed',
                    value=1,
                    metric_type='c',
                    az='default')
                )
        if self.params['socket']:
            for metric in metrics:
                self.push_metric(metric, self.params['socket'])
            self.exit(changed=True, pushed_metrics=metrics)
        self.fail_json(msg='socket must be set')


def main():
    module = LbLoadMonitoring()
    module()


if __name__ == '__main__':
    main()
