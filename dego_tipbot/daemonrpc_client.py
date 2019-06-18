from typing import Dict
from uuid import uuid4

import rpc_client
import json
import aiohttp
import asyncio

import sys
sys.path.append("..")
from config import config

class RPCException(Exception):
    def __init__(self, message):
        super(RPCException, self).__init__(message)


async def call_method(method_name: str, payload: Dict = None) -> Dict:
    url = f'http://{config.daemon.host}:{config.daemon.port}/json_rpc'
    full_payload = {
        'params': payload or {},
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': f'{method_name}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=full_payload, timeout=5) as response:
            res_data = await response.json()
            await session.close()
            return res_data['result']


async def gettopblock():
    url = f'http://{config.daemon.host}:{config.daemon.port}/json_rpc'
    result = await call_method('getblockcount')
    full_payload = {
        'jsonrpc': '2.0',
        'method': 'getblockheaderbyheight',
        'params': {'height': result['count'] - 1}
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=full_payload, timeout=5) as response:
            res_data = await response.json()
            await session.close()
            return res_data['result']


async def getWalletStatus():
    return await rpc_client.call_method('getStatus')
