#!/usr/bin/python3.6
import sys
from config import config
import store
import time
import asyncio


# Let's run balance update by a separate process
async def update_balance():
    print('sleep in second: 5 seconds')
    while True:
        time.sleep(5)
        start = time.time()
        try:
            await store.sql_update_balances()
            end = time.time()
            print('Done update balance: duration (s): '+str(end - start))
            print('Sleep in second: '+str(config.wallet_balance_update_interval))
            time.sleep(config.wallet_balance_update_interval)
        except Exception as e:
            print('Time out.. try again in 15s..')
            time.sleep(15)
            print(e)

loop = asyncio.get_event_loop()
loop.run_until_complete(update_balance())
loop.close()
