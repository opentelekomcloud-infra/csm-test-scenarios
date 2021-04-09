#!/usr/bin/python
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import abc

from ansible.module_utils.basic import AnsibleModule
from openstack.config import OpenStackConfig
from openstack.connection import Connection


def swift_full_argument_spec(**kwargs):
    spec = dict()
    spec.update(kwargs)
    return spec


class SwiftModule:
    """Openstack Module is a base class for all Message Module classes."""

    argument_spec = {}
    module_kwargs = {}

    def __init__(self):

        self.ansible = AnsibleModule(
            swift_full_argument_spec(**self.argument_spec),
            **self.module_kwargs)
        self.params = self.ansible.params
        self.module_name = self.ansible._name
        self.results = {'changed': False}
        self.exit = self.exit_json = self.ansible.exit_json
        self.fail = self.fail_json = self.ansible.fail_json

        self.cloud = OpenStackConfig().get_one()
        self.client = Connection(config=self.cloud).object_store

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
            self.ansible.log(f'[DEBUG] {msg}')

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
