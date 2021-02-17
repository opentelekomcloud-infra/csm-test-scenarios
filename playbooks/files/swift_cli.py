import json
from argparse import ArgumentParser

import requests
from openstack.config import OpenStackConfig

SWIFT_ENDPOINT = 'https://swift.eu-de.otc.t-systems.com'
OK_CODES = [200, 201, 202]


class SwiftClient:

    def __init__(self):
        self.session = requests.session()
        self.os_config = OpenStackConfig()
        self.cloud = self.os_config.get_one()

        self.iam_session = self.cloud.get_session()
        self.auth_url = self.iam_session.get_endpoint(service_type='identity')
        self.token = self.iam_session.get_token()
        self.project_id = self.iam_session.get_project_id()
        self.session.headers.update({'X-Auth-Token': self.token})
        self.base_url = f'{SWIFT_ENDPOINT}/v1/AUTH_{self.project_id}'
        self.response_format = 'format=json'

    def list_containers(self):
        try:
            response = self.session.get(
                f'{self.base_url}?{self.response_format}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return json.loads(response.text)
        return response.reason

    def list_container_objects(self, container):
        try:
            response = self.session.get(
                f'{self.base_url}/{container}?{self.response_format}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return json.loads(response.text)
        return response.reason

    def create_container(self, container):
        try:
            response = self.session.put(f'{self.base_url}/{container}')
        except ConnectionError as ce:
            raise ce
        return response.text

    def create_object(self, container, object_name, body: dict):
        try:
            response = self.session.put(
                f'{self.base_url}/{container}/{object_name}',
                data=json.dumps(body)
            )
        except ConnectionError as ce:
            raise ce
        return response.reason

    def object_content(self, container, object_name):
        try:
            response = self.session.get(
                f'{self.base_url}/{container}/{object_name}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return json.loads(response.text)
        return response.reason

    def delete_object(self, container, object_name):
        try:
            response = self.session.delete(
                f'{self.base_url}/{container}/{object_name}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return json.loads(response.text)
        return response.reason

    def delete_container(self, container):
        try:
            response = self.session.delete(
                f'{self.base_url}/{container}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return json.loads(response.text)
        return response.reason

def parse_params():
    parser = ArgumentParser(description='Swift operations')
    parser.add_argument('--method', '-m', required=True, default='GET')
    args = parser.parse_args()
    return args


def main():
    args = parse_params()
    client = SwiftClient()
    # client.list_containers()
    # client.list_container_objects(container='test')
    # client.create_container(container='test1')
    content = {
        "lb_monitoring": {
            "controller_key": "/tmp/data/key_csm_controller",
            "lb_ctrl_ip": "192.168.1.1",
            "lb_ecs_local_ips": ["192.168.1.10", "192.168.1.11", "192.168.1.12"],
            "lb_fip": "80.158.62.106"
        }
    }
    resp = client.create_object(container='test1', object_name='test', body=content)
    resp = client.object_content(container='test1', object_name='test')
    resp = client.delete_container(container='test1')
    resp = client.delete_object(container='test1', object_name='test')
    resp = client.delete_container(container='test1')
    print(resp)


if __name__ == '__main__':
    main()
