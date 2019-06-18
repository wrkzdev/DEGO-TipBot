from typing import Dict
from uuid import uuid4

import aiohttp
import asyncio
import json

import sys
sys.path.append("..")
from config import config

class RPCException(Exception):
    def __init__(self, message):
        super(RPCException, self).__init__(message)


async def call_method(method_name: str, payload: Dict = None) -> Dict:
    url = f'http://{config.wallet.host}:{config.wallet.port}/json_rpc'
    full_payload = {
        'params': payload or {},
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': f'{method_name}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=full_payload, timeout=10) as response:
            res_data = await response.read()
            res_data = res_data.decode('utf-8')
            await session.close()
            decoded_data = json.loads(res_data)
            return decoded_data['result']


async def call_method_sendwithdraw(method_name: str, payload: Dict = None) -> Dict:
    url = f'http://{config.withdrawwallet.host}:{config.withdrawwallet.port}/json_rpc'
    full_payload = {
        'params': payload or {},
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': f'{method_name}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=full_payload, timeout=10) as response:
            res_data = await response.read()
            res_data = res_data.decode('utf-8')
            await session.close()
            decoded_data = json.loads(res_data)
            return decoded_data['result']
