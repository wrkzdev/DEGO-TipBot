from typing import Dict
from uuid import uuid4

import rpc_client
import requests, json

import sys
sys.path.append("..")
from config import config

class RPCException(Exception):
    def __init__(self, message):
        super(RPCException, self).__init__(message)

def call_method(method_name: str, payload: Dict = None) -> Dict:
    full_payload = {
        'params': payload or {},
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': f'{method_name}'
    }
    resp = requests.post(
        f'http://{config.daemon.host}:{config.daemon.port}/json_rpc',
        json=full_payload, timeout=3.0)
    resp.raise_for_status()
    json_resp = resp.json()
    if 'error' in json_resp:
        raise RPCException(json_resp['error'])
    return resp.json().get('result', {})


def gettopblock():
    result = call_method('getblockcount')
    #print(result)
    data = '{"jsonrpc":"2.0","method":"getblockheaderbyheight","params":{"height":'+str(result['count'] - 1)+'}}'
    response = requests.post(f'http://{config.daemon.host}:{config.daemon.port}/json_rpc', data=data, timeout=3.0)
    json_resp = response.json()
    if 'error' in json_resp:
        raise RPCException(json_resp['error'])
    response.raise_for_status()
    json_resp = response.json()
    if 'error' in json_resp:
        raise RPCException(json_resp['error'])
    return response.json().get('result', {})


def getblock(blockH: str=None):
    data = '{"jsonrpc":"2.0","method":"getblockheaderbyheight","params":{"height":'+str(blockH)+'}}'
    response = requests.post(f'http://{config.daemon.host}:{config.daemon.port}/json_rpc', data=data, timeout=3.0)
    json_resp = response.json()
    if 'error' in json_resp:
        raise RPCException(json_resp['error'])
    response.raise_for_status()
    json_resp = response.json()
    if 'error' in json_resp:
        raise RPCException(json_resp['error'])
    return response.json().get('result', {})


def getblockbyHash(blockH: str=None):
    data = '{"jsonrpc":"2.0","method":"getblockheaderbyhash","params":{"hash":"'+str(blockH)+'"}}'
    response = requests.post(f'http://{config.daemon.host}:{config.daemon.port}/json_rpc', data=data, timeout=3.0)
    json_resp = response.json()
    if 'error' in json_resp:
        raise RPCException(json_resp['error'])
    response.raise_for_status()
    json_resp = response.json()
    if 'error' in json_resp:
        raise RPCException(json_resp['error'])
    return response.json().get('result', {})


def getWalletStatus():
    result = rpc_client.call_method('getStatus')
    return result

