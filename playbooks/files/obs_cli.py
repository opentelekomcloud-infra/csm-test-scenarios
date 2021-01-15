#!/usr/bin/env python3

import hashlib
import json
import os
from argparse import ArgumentParser
from dataclasses import dataclass

import requests
import yaml
from boto3.session import Session
from botocore.exceptions import ClientError
from openstack.config import OpenStackConfig

S3_ENDPOINT = 'https://obs.eu-de.otc.t-systems.com'
BUCKET = 'obs-csm'
RW_OWNER = 0o600


def parse_params():
    parser = ArgumentParser(description='Synchronize used private key with OBS')
    parser.add_argument('--key', '-k', required=True)
    parser.add_argument('--output', '-o', required=True)
    parser.add_argument('--local', action='store_true', default=False)
    parser.add_argument('--scenario_name')
    args = parser.parse_args()
    return args


@dataclass
class Credential:
    """Container for credential"""

    access: str
    secret: str
    security_token: str


def requires_update(file_name, remote_md5):
    """Check if local file is not up to date with remote"""
    if not os.path.isfile(file_name):
        return True
    with open(file_name, 'rb') as trg_file:
        md5 = hashlib.md5(trg_file.read()).hexdigest()
    return remote_md5 != md5


def get_key_from_s3(key_file, key_name, credential: Credential) -> str:
    """Download existing key from s3 or create a new one and upload"""

    session = Session(aws_access_key_id=credential.access,
                      aws_secret_access_key=credential.secret,
                      aws_session_token=credential.security_token)

    obs = session.resource('s3', endpoint_url=S3_ENDPOINT)
    bucket = obs.Bucket(BUCKET)
    try:
        file_md5 = bucket.Object(key_name).e_tag[1:-1]
    except ClientError as cl_e:
        if cl_e.response['Error']['Code'] == '404':
            print('The object does not exist in s3. Generating new one...')
        raise cl_e

    if requires_update(key_file, file_md5):
        bucket.download_file(key_name, key_file)
        print('Private key downloaded')
    return key_file


def _session_token_request():
    return {
        'auth': {
            'identity': {
                'methods': [
                    'token'
                ],
                'token': {
                    'duration-seconds': '900',
                }
            }
        }
    }


def _get_session_token(auth_url, os_token) -> Credential:
    v30_url = auth_url.replace('/v3', '/v3.0')
    token_url = f'{v30_url}/OS-CREDENTIAL/securitytokens'

    auth_headers = {'X-Auth-Token': os_token}

    response = requests.post(token_url, headers=auth_headers, json=_session_token_request())
    if response.status_code != 201:
        raise RuntimeError('Failed to get temporary AK/SK:', response.text)
    data = response.json()['credential']
    return Credential(data['access'], data['secret'], data['securitytoken'])


def acquire_temporary_ak_sk() -> Credential:
    """Get temporary AK/SK using password auth"""
    os_config = OpenStackConfig()
    cloud = os_config.get_one()

    iam_session = cloud.get_session()
    auth_url = iam_session.get_endpoint(service_type='identity')
    os_token = iam_session.get_token()
    return _get_session_token(auth_url, os_token)


def read_state(state_file) -> dict:
    """Load Terraform state from tfstate file to dict"""
    with open(state_file) as s_file:
        return json.load(s_file)


def generate_inventory(args):
    inv_output = {
        'all': {
            'hosts': {},
            'children': {}
        }
    }
    hosts = inv_output['all']['hosts']
    children = inv_output['all']['children']
    for name, attributes in get_ecs_instances(args.state):
        tags: dict = attributes.pop('tag', None) or {}
        hosts[name] = attributes
        if 'group' in tags:
            grp_name = tags['group']
            if grp_name not in children:
                children[grp_name] = {'hosts': {}}
            children[grp_name]['hosts'][name] = ''
    if hosts:
        root_path = os.path.abspath(f'{os.path.dirname(__file__)}/../..')
        path = f'{root_path}/inventory/prod/{args.name}.yml'
        with open(path, 'w+') as file:
            file.write(yaml.safe_dump(inv_output, default_flow_style=False))
        print(f'File written to: {path}')
    else:
        print('Nothing to write')


def get_instances_info(tf_state_file):
    tf_state = read_state(tf_state_file)
    for resource in tf_state['resources']:

        if resource['type'] == 'opentelekomcloud_compute_instance_v2':
            for instance in resource['instances']:
                tf_attrib = instance['attributes']

                name = tf_attrib['name']
                attributes = {
                    'id': tf_attrib['id'],
                    'image': tf_attrib['image_name'],
                    'region': tf_attrib['region'],
                    'public_ipv4': tf_attrib['network'][0]['floating_ip'],
                    'ansible_host': tf_attrib['access_ip_v4'],
                    'ansible_ssh_user': 'linux',
                    'tag': tf_attrib['tag'],
                }

                yield name, attributes


def main():
    """Run the script"""
    args = parse_params()

    key_file = args.output
    credential = acquire_temporary_ak_sk()
    key_file = get_key_from_s3(key_file, args.key, credential)
    generate_inventory(args)
    os.chmod(key_file, RW_OWNER)


if __name__ == '__main__':
    main()
