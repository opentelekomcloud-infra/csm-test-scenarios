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
import json
import os

import yaml
from ansible.module_utils.swift import SwiftModule

DOCUMENTATION = '''
---
module: swift_client
short_description: Client for OBS swift.
version_added: "1.0.0"
author: "Anton Sidelnikov (@anton-sidelnikov)"
description:
options:
  container:
    description: Container name.
    type: str
  object_name:
    description: Name of the object.
    type: str
  content:
    description: Content to upload, can be filepath or variable.
    type: str
  state:
    description: State.
    type: int
    choices=[present, absent, fetch]
    default: present
requirements: []
'''

RETURN = '''
'''

EXAMPLES = '''
- name: Swift create object from yaml file
  swift_client:
    state: present
    container: test
    object_name: object
    content: /home/linux/test.yaml
  register: result

- name: Swift create object from variable
  swift_client:
    state: present
    container: test
    object_name: object
    content:
      obj:
        var1: 1
        var2: 2
  register: result
      
- name: Swift list containers
  swift_client:
    state: fetch
  register: result

- name: Swift container objects list
  swift_client:
    state: fetch
    container: csm
  register: result

- name: Swift container object content
  swift_client:
    state: fetch
    container: csm
    object_name: lb_monitoring_inventory
  register: result
  
- name: Swift delete object
  swift_client:
    state: absent
    container: test
    object_name: object
  register: result

- name: Swift delete empty container
  swift_client:
    state: absent
    container: test
  register: r
'''


def is_path(path):
    """ Check if it file path"""
    if os.path.isfile(path):
        return True
    return False


def read_yaml(path):
    """
    Reads yaml file

    :param path: path to file
    :return: yaml file data as dict
    """
    with open(path, 'r') as file:
        data = yaml.safe_load(file)
    return json.dumps(data)


class SwiftClient(SwiftModule):
    argument_spec = dict(
        container=dict(type='str', required=False),
        object_name=dict(type='str', required=False),
        state=dict(required=False, choices=['present', 'absent', 'fetch'], default='present'),
        content=dict(type='str', required=False)
    )

    def run(self):
        changed = False
        container = self.params['container']
        object_name = self.params['object_name']
        state = self.params['state']
        content = self.params['content']
        data = []
        if state == 'present':
            containers = [item['name'] for item in self.client.containers()]
            if container not in containers:
                data = self.client.create_container(container)
                data.pop('location')
                changed = True
            if content and object_name:
                if is_path(content):
                    content = read_yaml(content)
                else:
                    content = content.replace("'", "\"")
                raw = self.client.create_object(
                    container=container,
                    name=object_name,
                    data=content
                )
                dt = raw.to_dict()
                dt.pop('location')
                data.append(dt)
                changed = True
            self.exit(changed=changed, data=data)
        if state == 'absent':
            if object_name:
                data = self.client.delete_object(
                    container=container,
                    obj=object_name
                )
                self.exit(changed=changed, deleted_object=data)
            data = self.client.delete_container(container=container)
            self.exit(changed=changed, deleted_container=data)
        if state == 'fetch':
            if container and object_name:
                data = self.client.download_object(object_name, container)
                self.exit(changed=changed, object=json.loads(data))
            if container:
                for raw in self.client.objects(container):
                    dt = raw.to_dict()
                    dt.pop('location')
                    data.append(dt)
                    self.exit(changed=changed, objects=data)
            for raw in self.client.containers():
                dt = raw.to_dict()
                dt.pop('location')
                data.append(dt)
                self.exit(changed=changed, containers=data)


def main():
    module = SwiftClient()
    module()


if __name__ == '__main__':
    main()
