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
from time import sleep

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
  request_count:
    description: Count of requests.
    type: int
    default: 30
  type:
    description: Public or internal address.
    type: str
    default: public
    choices=['public', 'internal']
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
        type=dict(type='str', default='public', choices=['public', 'internal'])
    )

    def run(self):
        timeout = self.params['timeout']
        type = self.params['type']
        address = f"{self.params['protocol']}://{self.params['target_address']}"
        metrics = []
        for _ in range(self.params['request_count']):
            try:
                res = requests.get(address, headers={'Connection': 'close'}, timeout=timeout)
            except requests.Timeout:
                self.log('timeout sending request to LB')
                metrics.append(self.create_metric(
                    name=f'{TIMEOUT_METRIC}.{type}',
                    value=timeout * 1000,
                    metric_type='ms',
                    az='default')
                )
            else:
                metrics.append(self.create_metric(
                    name=f'{SUCCESS_METRIC}.{type}',
                    value=int(res.elapsed.microseconds / 1000),
                    metric_type='ms',
                    az=re.search(r'eu-de-\d+', res.headers['Server']).group()
                ))
            sleep(1)
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
