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
import os

from ansible.module_utils.swift import SwiftModule
from openstack.exceptions import ResourceNotFound

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
  register: result
'''


class SwiftClient(SwiftModule):
    argument_spec = dict(
        container=dict(type='str', required=False),
        object_name=dict(type='str', required=False),
        state=dict(required=False, choices=['present', 'absent', 'fetch'], default='present'),
        content=dict(type='str', required=False)
    )

    def present(self, container, object_name=None):
        """Ensure container and object exist

        If `object_name` is not set, just creates container if missing

        If `content` and `object_name` is set, file upload will be done
        """

        data = {}
        changed = False

        try:
            container_data = self.client.get_container_metadata(container).to_dict()
        except ResourceNotFound:
            container_data = self.client.create_container(container).to_dict()
            changed = True
        container_data.pop('location')
        data['container'] = container_data

        content = self.params['content']
        if content and object_name:
            if os.path.isfile(content):
                with open(content) as file:
                    content = file.read()
            raw = self.client.create_object(
                container=container,
                name=object_name,
                data=content
            )
            object_data = raw.to_dict()
            object_data.pop('location')
            object_data['content'] = content
            data['object'] = object_data
            changed = True

        self.exit(changed=changed, **data)

    def _container_exist(self, name):
        try:
            self.client.get_container_metadata(name)
            return True
        except ResourceNotFound:
            return False

    def _object_exist(self, container, name):
        try:
            self.client.get_object_metadata(name, container)
            return True
        except ResourceNotFound:
            return False

    def absent(self, container, object_name=None):
        """Remove object and its container"""

        if not self._container_exist(container):
            self.exit(changed=False)

        if object_name and self._object_exist(container, object_name):
            self.client.delete_object(
                container=container,
                obj=object_name
            )

        self.client.delete_container(container=container)
        self.exit(changed=True)

    def fetch(self, container=None, object_name=None):
        """Fetches current state

        If container and object name is set, downloads the file
        returning it in `object.content`

        If only container is set, list all objects of the container

        If neither are set, list all containers in the project
        """
        if container and object_name:
            content = self.client.download_object(object_name, container)
            self.exit(changed=False, object=dict(content=content))

        if container:
            objects = []
            for raw in self.client.objects(container):
                dt = raw.to_dict()
                dt.pop('location')
                objects.append(dt)
            self.exit(changed=False, objects=objects)

        containers = []
        for raw in self.client.containers():
            dt = raw.to_dict()
            dt.pop('location')
            containers.append(dt)
        self.exit(changed=False, containers=containers)

    def run(self):
        container = self.params['container']
        object_name = self.params['object_name']
        state = self.params['state']
        if state == 'present':
            self.present(container, object_name)
        if state == 'absent':
            self.absent(container, object_name)
        if state == 'fetch':
            self.fetch(container, object_name)


def main():
    module = SwiftClient()
    module()


if __name__ == '__main__':
    main()
