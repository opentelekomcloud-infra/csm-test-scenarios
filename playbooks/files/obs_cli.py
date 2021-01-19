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
ROOT_PATH = os.path.abspath(f'{os.path.dirname(__file__)}/../..')


def parse_params():
    parser = ArgumentParser(description='Synchronize used private key with OBS')
    parser.add_argument('--key_name', '-k', required=True, default='key_csm_controller')
    parser.add_argument('--scenario_name', '-s', nargs='+', required=True,
                        default=['csm_controller'])
    parser.add_argument('--terraform_workspace', '-w', required=True, default='test')
    parser.add_argument('--output', '-o', required=True, default='/tmp/data')
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


def get_item_from_s3(file, item_name, credential: Credential) -> str:
    """Download existing item from s3"""

    session = Session(aws_access_key_id=credential.access,
                      aws_secret_access_key=credential.secret,
                      aws_session_token=credential.security_token)

    obs = session.resource('s3', endpoint_url=S3_ENDPOINT)
    bucket = obs.Bucket(BUCKET)
    try:
        file_md5 = bucket.Object(item_name).e_tag[1:-1]
    except ClientError as cl_e:
        if cl_e.response['Error']['Code'] == '404':
            print('The object does not exist in s3.')
        raise cl_e

    if requires_update(file, file_md5):
        bucket.download_file(item_name, file)
        print('Private key downloaded')
    return file


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


def generate_vars_file(state, key_path):
    inv_output = {
        'controller_state': {
            'controller_key': key_path
        }
    }
    variables = inv_output['controller_state']
    variables.update(get_instances_info(state))
    path = f'{ROOT_PATH}/playbooks/vars/{os.path.basename(state)}.yml'
    with open(path, 'w+') as file:
        file.write(yaml.safe_dump(inv_output, default_flow_style=False))
    print(f'File written to: {path}')


def get_instances_info(tf_state_file):
    tf_state = read_state(tf_state_file)
    return {name: tf_state['outputs'][name]['value'] for name in tf_state['outputs']}


def main():
    """
    Script to prepare key and state variables
    Creates var file for ansible in playbooks/vars folder
    """
    args = parse_params()
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    key_file = f'{args.output}/{args.key_name}'
    credential = acquire_temporary_ak_sk()
    key_file = get_item_from_s3(
        key_file,
        f'key/{args.key_name}',
        credential)
    os.chmod(key_file, RW_OWNER)

    for state in args.scenario_name:
        path = f'{args.output}/{state}'
        get_item_from_s3(
            path,
            f'env:/{args.terraform_workspace}/terraform_state/{state}',
            credential)
        generate_vars_file(
            path,
            key_file
        )


if __name__ == '__main__':
    main()
