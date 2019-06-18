from typing import List, Dict
import json
from uuid import uuid4
import sys
sys.path.append("..")
import rpc_client
import requests
from config import config
import asyncio


async def register() -> str:
    result = await rpc_client.call_method('createAddress')
    reg_address = {}
    reg_address['address'] = result['address']
    reg_address['privateSpendKey'] = getSpendKey(result['address'])
    ## Avoid any crash and nothing to restore or import
    print('Wallet register: '+reg_address['address']+'=>privateSpendKey: '+reg_address['privateSpendKey'])
    ## End print log ID,spendkey to log file
    return reg_address

async def getSpendKey(from_address: str) -> str:
    payload = {
        'address': from_address
    }
    result = await rpc_client.call_method('getSpendKeys', payload=payload)
    return result['spendSecretKey']


async def send_transaction(to_address: str, amount: int) -> str:
    payload = {
        'addresses': [config.withdrawwallet.address],
        'transfers': [{
            "amount": amount,
            "address": to_address
        }],
        'fee': config.tx_fee,
        'anonymity': config.withdrawwallet.mixin
    }
    retry = config.TxRetry
    result = None
    while retry > 0:
        result = await rpc_client.call_method_sendwithdraw('sendTransaction', payload=payload)
        if result:
            if 'transactionHash' in result:
                break
        retry = retry - 1
    return result['transactionHash']


async def send_transaction_id(to_address: str, amount: int, paymentid: str) -> str:
    payload = {
        'addresses': [config.withdrawwallet.address],
        'transfers': [{
            "amount": amount,
            "address": to_address
        }],
        'fee': config.tx_fee,
        'anonymity': config.withdrawwallet.mixin,
        'paymentId': paymentid
    }
    retry = config.TxRetry
    result = None
    while retry > 0:
        result = await rpc_client.call_method_sendwithdraw('sendTransaction', payload=payload)
        if result:
            if 'transactionHash' in result:
                break
        retry = retry - 1
    return result['transactionHash']


async def get_all_balances_all() -> Dict[str, Dict]:
    walletCall = await rpc_client.call_method('getAddresses')
    wallets = [] ## new array
    for address in walletCall['addresses']:
        wallet = await rpc_client.call_method('getBalance', {'address': address})
        wallets.append({'address':address,'unlocked':wallet['availableBalance'],'locked':wallet['lockedAmount']})
    return wallets


async def get_some_balances(wallet_addresses: List[str]) -> Dict[str, Dict]:
    wallets = [] ## new array
    for address in wallet_addresses:
        wallet = await rpc_client.call_method('getBalance', {'address': address})
        wallets.append({'address':address,'unlocked':wallet['availableBalance'],'locked':wallet['lockedAmount']})
    return wallets

async def get_balance_address(address: str) -> Dict[str, Dict]:
    result = await rpc_client.call_method('getBalance', {'address': address})
    return result


def wallet_optimize_single(subaddress: str, threshold: int) -> int:
    params = {
        "threshold": threshold,
        "anonymity": config.wallet.mixin,
        "addresses": [
            subaddress
        ],
        "destinationAddress": subaddress
    }

    full_payload = {
        'params': params or {},
        'jsonrpc': '2.0',
        'id': str(uuid4()),
        'method': 'sendFusionTransaction'
    }

    print('Optimizing wallet: '+subaddress)
    i=0
    while True:
        print('subaddress: '+ subaddress)
        resp = requests.post(f'http://{config.wallet.host}:{config.wallet.port}/json_rpc', json=full_payload)
        try:
            resp.raise_for_status()
            json_resp = resp.json()
            if 'error' in json_resp:
                break
            json_resp = resp.json().get('result', {})
            if 'transactionHash' in json_resp:
                i = i+1
        except requests.exceptions.HTTPError as e:
            print("Fusion Error: " + str(e))
            break
    return i
