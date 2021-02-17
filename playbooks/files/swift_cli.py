#!/usr/bin/env python3
import json
import os
import sys
from argparse import ArgumentParser

import requests
import yaml
from openstack.config import OpenStackConfig

SWIFT_ENDPOINT = 'https://swift.eu-de.otc.t-systems.com'
OK_CODES = [200, 201, 202]


class SwiftClient:
    """Class for Swift interactions"""
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

    def list_containers(self) -> dict:
        """
        List of available Swift containers
        :return: dict of available containers
        """
        try:
            response = self.session.get(
                f'{self.base_url}?{self.response_format}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return json.loads(response.text)

    def list_container_objects(self, container) -> dict:
        """
        List objects in container
        :param container: container name
        :return: dict of available container objects
        """
        try:
            response = self.session.get(
                f'{self.base_url}/{container}?{self.response_format}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return json.loads(response.text)

    def create_container(self, container):
        """
        Creates container
        :param container: container name
        :return:
        """
        try:
            response = self.session.put(f'{self.base_url}/{container}')
        except ConnectionError as ce:
            raise ce
        return response.text

    def create_object(self, container, object_name, body: dict):
        """
        Creates object in selected container
        :param container: container name
        :param object_name: object name
        :param body: content
        :return:
        """
        try:
            response = self.session.put(
                f'{self.base_url}/{container}/{object_name}',
                data=json.dumps(body)
            )
        except ConnectionError as ce:
            raise ce
        return response.reason

    def object_content(self, container, object_name):
        """
        Returns object content
        :param container: container name
        :param object_name: object name
        :return:
        """
        try:
            response = self.session.get(
                f'{self.base_url}/{container}/{object_name}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return response.text
        return response.reason

    def delete_object(self, container, object_name):
        """
        Deletes object in selected container
        :param container: container name
        :param object_name: object name
        :return:
        """
        try:
            response = self.session.delete(
                f'{self.base_url}/{container}/{object_name}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return response.text
        return response.reason

    def delete_container(self, container):
        """
        Deletes empty container
        :param container: container name
        :return:
        """
        try:
            response = self.session.delete(
                f'{self.base_url}/{container}'
            )
        except ConnectionError as ce:
            raise ce
        if response.status_code in OK_CODES:
            return response.text
        return response.reason


def is_path(path):
    """ Check if it file path"""
    if os.path.isfile(path):
        return True
    return False


def read_yaml(path) -> dict:
    """
    Reads yaml file
    :param path: path to file
    :return: yaml file data as dict
    """
    with open(path, 'r') as file:
        data = yaml.safe_load(file)
    return data


def parse_params():
    parser = ArgumentParser(description='Swift operations')
    parser.add_argument('--container', '-с', required=True)
    parser.add_argument('--object_name', '-o', required=False)
    parser.add_argument('--state', '-s', required=False, default='present',
                        choices=['present', 'absent', 'fetch'])
    parser.add_argument('--content', '-cn', required=False)

    args = parser.parse_args()
    return args


def main():
    args = parse_params()
    client = SwiftClient()

    if args.state == 'present':
        containers = [item['name'] for item in client.list_containers()]
        if args.container not in containers:
            result = client.create_container(container=args.container)
            return print(result)
        if args.content and args.object_name:
            if is_path(args.content):
                args.content = read_yaml(args.content)
                result = client.create_object(
                    container=args.container,
                    object_name=args.object_name,
                    body=args.content
                )
                return print(result)
        return print('No content or object_name', file=sys.stderr)

    if args.state == 'absent':
        if args.object_name:
            result = client.delete_object(
                container=args.container,
                object_name=args.object_name
            )
            return print(result)
        result = client.delete_container(container=args.container)
        return print(result)

    if args.state == 'fetch':
        if args.object_name:
            result = client.object_content(
                container=args.container,
                object_name=args.object_name
            )
            return print(result)
        result = client.list_container_objects(args.container)
        return print(result)


if __name__ == '__main__':
    main()
