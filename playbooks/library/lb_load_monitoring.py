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
import logging

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
  lb_ip:
    description: IP address of target load balancer.
    type: str
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
import os
import requests

from .common.message import Metric, push_metric
from ansible.module_utils.basic import AnsibleModule
from time import sleep

LB_TIMING = 'csm_lb_timings'
LB_TIMEOUT = 'csm_lb_timeout'

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

INSTANCES_AZ = {
    'lb-monitoring-instance0-prod': 'eu-de-01',
    'lb-monitoring-instance1-prod': 'eu-de-02',
    'lb-monitoring-instance2-prod': 'eu-de-03',
}

SOCKET = os.getenv("APIMON_PROFILER_MESSAGE_SOCKET", "")


class LbLoadMonitoring(AnsibleModule):
    module = AnsibleModule(
        argument_spec=dict(
            lb_ip=dict(type='str', required=True)
        )
    )

    def run(self):

        timeout = 20
        metrics = []
        for _ in range(15):
            try:
                res = requests.get(f"http://{self.params['lb_ip']}", headers={'Connection': 'close'}, timeout=timeout)
            except requests.Timeout as ex:
                LOGGER.exception('Timeout sending request to LB')
                metrics.append(Metric(
                    name=LB_TIMEOUT,
                    value=timeout * 1000,
                    metric_type='ms',
                    az='Timeout')
                )
            else:
                metrics.append(Metric(
                    name=LB_TIMING,
                    value=int(res.elapsed.microseconds / 1000),
                    metric_type='ms',
                    az=INSTANCES_AZ.get(res.headers['Server']))
                )
            sleep(1)
        if SOCKET:
            for metric in metrics:
                push_metric(metric, SOCKET)

        self.exit(changed=False, pushed_metrics=metrics)


def main():
    module = LbLoadMonitoring()
    module()


if __name__ == '__main__':
    main()
