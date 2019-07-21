from typing import List
from datetime import datetime
import time
import json

import traceback
import sys
# Encrypt
from cryptography.fernet import Fernet

sys.path.append("..")
import wallet, daemonrpc_client
from config import config
import asyncio

# MySQL
import pymysql, pymysqlpool
import pymysql.cursors

pymysqlpool.logger.setLevel('DEBUG')
myconfig = {
    'host': config.mysql.host,
    'user':config.mysql.user,
    'password':config.mysql.password,
    'database':config.mysql.db,
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit':True
    }

connPool = pymysqlpool.ConnectionPool(size=5, name='connPool', **myconfig)
conn = connPool.get_connection(timeout=5, retry_num=2)

# OpenConnection
def openConnection():
    global conn, connPool
    try:
        if conn is None:
            conn = connPool.get_connection(timeout=5, retry_num=2)
    except:
        print("ERROR: Unexpected error: Could not connect to MySql instance.")
        sys.exit()


async def sql_update_balances():
    print('SQL: Updating all wallet balances')
    balances = await wallet.get_all_balances_all()
    try:
        openConnection()
        with conn.cursor() as cur:
            for details in balances:
                sql = """ INSERT INTO dego_walletapi (`balance_wallet_address`, `actual_balance`, `locked_balance`, `lastUpdate`) 
                          VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE `actual_balance`=%s, `locked_balance`=%s, `lastUpdate`=%s """
                cur.execute(sql, (details['address'], details['unlocked'], details['locked'], int(time.time()), details['unlocked'], details['locked'], int(time.time()),))
                conn.commit()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def sql_update_some_balances(wallet_addresses: List[str]):
    print('SQL: Updating some wallet balances')
    balances = await wallet.get_some_balances(wallet_addresses)
    try:
        openConnection()
        with conn.cursor() as cur:
            for details in balances:
                sql = """ INSERT INTO dego_walletapi (`balance_wallet_address`, `actual_balance`, `locked_balance`, `lastUpdate`) 
                          VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE `actual_balance`=%s, `locked_balance`=%s, `lastUpdate`=%s """
                cur.execute(sql, (details['address'], details['unlocked'], details['locked'], int(time.time()), details['unlocked'], details['locked'], int(time.time()),))
                conn.commit()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def sql_register_user(userID):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT user_id, balance_wallet_address, user_wallet_address FROM dego_user WHERE `user_id`=%s LIMIT 1 """
            cur.execute(sql, (userID))
            result = cur.fetchone()
            if result is None:
                balance_address = await wallet.register()
                if balance_address is None:
                   print('Internal error during call register wallet-api')
                   return
                else:
                   walletStatus = await daemonrpc_client.getWalletStatus()
                   if walletStatus is None:
                       print('Can not reach wallet-api during sql_register_user')
                       chainHeight = 0
                   else:
                       chainHeight = int(walletStatus['blockCount']) # reserve 20
                   sql = """ INSERT INTO dego_user (`user_id`, `balance_wallet_address`, `balance_wallet_address_ts`, `balance_wallet_address_ch`, `privateSpendKey`) 
                             VALUES (%s, %s, %s, %s, %s) """
                   cur.execute(sql, (str(userID), balance_address['address'], int(time.time()), chainHeight, encrypt_string(balance_address['privateSpendKey']), ))
                   conn.commit()
                   return True
            else:
                return result
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def sql_update_user(userID, user_wallet_address):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT user_id, user_wallet_address, balance_wallet_address FROM dego_user WHERE `user_id`=%s LIMIT 1 """
            cur.execute(sql, (userID))
            result = cur.fetchone()
            if result is None:
                balance_address = await wallet.register()
                if balance_address is None:
                   print('Internal error during call register wallet-api')
                   return
            else:
                sql = """ UPDATE dego_user SET user_wallet_address=%s WHERE user_id=%s """
                cur.execute(sql, (user_wallet_address, str(userID),))
                conn.commit()
                result2 = result
                result2['user_wallet_address'] = user_wallet_address
                return result2
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


async def sql_get_userwallet(userID):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT user_id, balance_wallet_address, user_wallet_address, balance_wallet_address_ts, balance_wallet_address_ch, lastOptimize 
                      FROM dego_user WHERE `user_id`=%s LIMIT 1 """
            cur.execute(sql, (str(userID),))
            result = cur.fetchone()
            if result is None:
                return None
            else:
                userwallet = result
                sql = """ SELECT balance_wallet_address, actual_balance, locked_balance, lastUpdate FROM dego_walletapi 
                          WHERE `balance_wallet_address`=%s LIMIT 1 """
                cur.execute(sql, (userwallet['balance_wallet_address'],))
                result = cur.fetchone()
                if result:
                    userwallet['actual_balance'] = int(result['actual_balance'])
                    userwallet['locked_balance'] = int(result['locked_balance'])
                    userwallet['lastUpdate'] = int(result['lastUpdate'])
                else:
                    userwallet['actual_balance'] = 0
                    userwallet['locked_balance'] = 0
                return userwallet
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_get_countLastTx(userID, lastDuration: int):
    lapDuration = int(time.time()) - lastDuration
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT `user_id`,`date` FROM dego_external_tx WHERE `user_id` = %s AND `date`>%s
                      ORDER BY `date` DESC LIMIT 10 """
            cur.execute(sql, (str(userID), lapDuration,))
            result = cur.fetchall()
            if result is None:
                return 0
            else:
                return len(result)
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_mv_tx_single(user_from: str, user_name: str, to_user: str, server_id: str, servername: str, messageid: str, amount: int, tiptype: str):
    global conn
    if tiptype.upper() not in ["TIP", "DONATE"]:
        return False
    try:
        openConnection()
        with conn.cursor() as cur: 
            sql = """ INSERT INTO dego_mv_tx (`from_userid`, `from_name`, `to_userid`, `server_id`, `server_name`, `message_id`, `amount`, `type`, `date`) 
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) """
            cur.execute(sql, (user_from, user_name, to_user, server_id, servername, messageid, amount, tiptype.upper(), int(time.time()),))
            conn.commit()
        return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return False


def sql_mv_tx_multiple(user_from: str, user_name: str, user_tos, server_id: str, servername: str, messageid: str, amount_each: int, tiptype: str):
    # user_tos is array "account1", "account2", ....
    global conn
    if tiptype.upper() not in ["TIPS", "TIPALL"]:
        return False
    values_str = []
    currentTs = int(time.time())
    for item in user_tos:
        values_str.append(f"('{user_from}', '{user_name}', '{item}', '{server_id}', '{servername}', '{messageid}', {amount_each}, '{tiptype.upper()}', {currentTs})\n")
    values_sql = "VALUES " + ",".join(values_str)
    try:
        openConnection()
        with conn.cursor() as cur: 
            sql = """ INSERT INTO dego_mv_tx (`from_userid`, `from_name`, `to_userid`, `server_id`, `server_name`, `message_id`, `amount`, `type`, `date`) 
                      """+values_sql+""" """
            cur.execute(sql,)
            conn.commit()
        return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return False


def sql_adjust_balance(userID: str):
    global conn
    try:
        openConnection()
        with conn.cursor() as cur: 
            sql = """ SELECT SUM(amount) AS Expense FROM dego_mv_tx WHERE `from_userid`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                Expense = result['Expense']
            else:
                Expense = 0

            sql = """ SELECT SUM(amount) AS Income FROM dego_mv_tx WHERE `to_userid`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                Income = result['Income']
            else:
                Income = 0

            sql = """ SELECT SUM(amount) AS DepositWallet FROM dego_deposit_towallet WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                DepositWallet = result['DepositWallet']
            else:
                DepositWallet = 0

            sql = """ SELECT SUM(amount) AS TxExpense FROM dego_external_tx WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                TxExpense = result['TxExpense']
            else:
                TxExpense = 0

            sql = """ SELECT SUM(fee) AS TxWithdraw FROM dego_external_tx WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                TxWithdraw = result['TxWithdraw']
            else:
                TxWithdraw = 0

            sql = """ SELECT SUM(fee) AS IntFeeExpense FROM dego_deposit_towallet WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                IntFeeExpense = result['IntFeeExpense']
            else:
                IntFeeExpense = 0

            balance = {}
            balance['Expense'] = Expense or 0
            balance['Income'] = Income or 0
            balance['DepositWallet'] = DepositWallet or 0
            balance['TxExpense'] = TxExpense or 0
            balance['TxWithdraw'] = TxWithdraw or 0
            balance['IntFeeExpense'] = IntFeeExpense or 0
            balance['Adjust'] = int(balance['DepositWallet'] + balance['Income'] - balance['Expense'] - balance['TxExpense'] - balance['TxWithdraw'] - balance['IntFeeExpense'])

            return balance
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return False


async def sql_send_tip_Ex(user_from: str, address_to: str, amount: int, txtype: str):
    if txtype.upper() not in ["SEND", "WITHDRAW"]:
        return None
    user_from_wallet = await sql_get_userwallet(user_from)
    tx_hash = None
    if 'balance_wallet_address' in user_from_wallet:
        tx_hash = await wallet.send_transaction(address_to, amount)
        if tx_hash:
            try:
                openConnection()
                with conn.cursor() as cur:
                   sql = """ INSERT INTO dego_external_tx (`user_id`, `amount`, `fee`, `to_address`, `type`, `date`, `tx_hash`) VALUES (%s, %s, %s, %s, %s, %s, %s) """
                   cur.execute(sql, (user_from, amount, config.tx_fee, address_to, txtype.upper(), int(time.time()), tx_hash,))
                   conn.commit()
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
            return tx_hash
    else:
        return None


async def sql_send_tip_Ex_id(user_from: str, address_to: str, amount: int, paymentid: str, txtype: str):
    if txtype.upper() not in ["SEND", "WITHDRAW"]:
        return None
    user_from_wallet = await sql_get_userwallet(user_from)
    tx_hash = None
    if 'balance_wallet_address' in user_from_wallet:
        tx_hash = await wallet.send_transaction_id(address_to, amount, paymentid)
        if tx_hash:
            updateTime = int(time.time())
            try:
                openConnection()
                with conn.cursor() as cur:
                   timestamp = int(time.time())
                   sql = """ INSERT INTO dego_external_tx (`user_id`, `amount`, `fee`, `to_address`, `paymentid`, `type`, `date`, `tx_hash`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) """
                   cur.execute(sql, (user_from, amount, config.tx_fee, address_to, paymentid, txtype.upper(), int(time.time()), tx_hash,))
                   conn.commit()
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
            return tx_hash
    else:
        return None


def sql_tag_by_server(server_id: str, tag_id: str=None):
    try:
        openConnection()
        with conn.cursor() as cur:
            if tag_id is None: 
                sql = """ SELECT tag_id, tag_desc, date_added, tag_serverid, added_byname, added_byuid, num_trigger FROM dego_tag WHERE tag_serverid = %s """
                cur.execute(sql, (server_id,))
                result = cur.fetchall()
                tag_list = []
                for row in result:
                    tag_list.append({'tag_id':row[0], 'tag_desc':row[1], 'date_added':row[2], 'tag_serverid':row[3], 'added_byname':row[4], 'added_byuid':row[5], 'num_trigger':row[6]})
                return tag_list
            else:
                sql = """ SELECT `tag_id`, `tag_desc`, `date_added`, `tag_serverid`, `added_byname`, `added_byuid`, `num_trigger` FROM dego_tag WHERE tag_serverid = %s AND tag_id=%s """
                cur.execute(sql, (server_id, tag_id,))
                result = cur.fetchone()
                if result:
                    tag = result
                    sql = """ UPDATE dego_tag SET num_trigger=num_trigger+1 WHERE tag_serverid = %s AND tag_id=%s """
                    cur.execute(sql, (server_id, tag_id,))
                    conn.commit()
                    return tag
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_tag_by_server_add(server_id: str, tag_id: str, tag_desc: str, added_byname: str, added_byuid: str):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT COUNT(tag_serverid) as Num_Tag FROM dego_tag WHERE tag_serverid=%s """
            cur.execute(sql, (server_id,))
            counting = cur.fetchone()
            if counting:
                if counting['Num_Tag'] > 20:
                    return None
            sql = """ SELECT `tag_id`, `tag_desc`, `date_added`, `tag_serverid`, `added_byname`, `added_byuid`, `num_trigger` 
                      FROM dego_tag WHERE tag_serverid = %s AND tag_id=%s """
            cur.execute(sql, (server_id, tag_id.upper(),))
            result = cur.fetchone()
            if result is None:
                sql = """ INSERT INTO dego_tag (`tag_id`, `tag_desc`, `date_added`, `tag_serverid`, `added_byname`, `added_byuid`) 
                          VALUES (%s, %s, %s, %s, %s, %s) """
                cur.execute(sql, (tag_id.upper(), tag_desc, int(time.time()), server_id, added_byname, added_byuid,))
                conn.commit()
                return tag_id.upper()
            else:
                return None
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_tag_by_server_del(server_id: str, tag_id: str):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT `tag_id`, `tag_desc`, `date_added`, `tag_serverid`, `added_byname`, `added_byuid`, `num_trigger` 
                      FROM dego_tag WHERE tag_serverid = %s AND tag_id=%s """
            cur.execute(sql, (server_id, tag_id.upper(),))
            result = cur.fetchone()
            if result is None:
                return None
            else:
                sql = """ DELETE FROM dego_tag WHERE `tag_id`=%s AND `tag_serverid`=%s """
                cur.execute(sql, (tag_id.upper(), server_id,))
                conn.commit()
                return tag_id.upper()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_add_messages(list_messages):
    if len(list_messages) == 0:
        return 0
    global conn
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ INSERT IGNORE INTO `discord_messages` (`serverid`, `server_name`, `channel_id`, `channel_name`, `user_id`, 
                      `message_author`, `message_id`, `message_time`)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s) """
            cur.executemany(sql, list_messages)
            conn.commit()
            return cur.rowcount
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_get_messages(server_id: str, channel_id: str, time_int: int):
    global conn
    lapDuration = int(time.time()) - time_int
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT DISTINCT `user_id` FROM discord_messages 
                      WHERE `serverid` = %s AND `channel_id` = %s AND `message_time`>%s """
            cur.execute(sql, (server_id, channel_id, lapDuration,))
            result = cur.fetchall()
            list_talker = []
            if result:
                for item in result:
                    if int(item['user_id']) not in list_talker:
                        list_talker.append(int(item['user_id']))
            return list_talker
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_get_tipnotify():
    global conn
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT `user_id`, `date` FROM bot_tipnotify_user """
            cur.execute(sql,)
            result = cur.fetchall()
            ignorelist = []
            for row in result:
                ignorelist.append(row['user_id'])
            return ignorelist
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_toggle_tipnotify(user_id: str, onoff: str):
    # Bot will add user_id if it failed to DM
    global conn
    onoff = onoff.upper()
    if onoff == "OFF":
        try:
            openConnection()
            with conn.cursor() as cur:
                sql = """ INSERT IGNORE INTO `bot_tipnotify_user` (`user_id`, `date`)
                          VALUES (%s, %s) """
                cur.execute(sql, (user_id, int(time.time())))
                conn.commit()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
    elif onoff == "ON":
        try:
            openConnection()
            with conn.cursor() as cur:
                sql = """ DELETE FROM `bot_tipnotify_user` WHERE `user_id` = %s """
                cur.execute(sql, str(user_id))
                conn.commit()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)


def sql_change_userinfo_single(user_id: str, what: str, value: str):
    global conn
    try:
        openConnection()
        with conn.cursor() as cur:
            # select first
            sql = """ SELECT `user_id` FROM discord_userinfo 
                      WHERE `user_id` = %s """
            cur.execute(sql, (user_id,))
            result = cur.fetchone()
            if result:
                sql = """ UPDATE discord_userinfo SET `""" + what.lower() + """` = %s WHERE `user_id` = %s """
                cur.execute(sql, (value, user_id))
                conn.commit()
            else:
                sql = """ INSERT INTO `discord_userinfo` (`user_id`, `""" + what.lower() + """`)
                      VALUES (%s, %s) """
                cur.execute(sql, (user_id, value))
                conn.commit()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


def sql_discord_userinfo_get(user_id: str):
    global conn
    try:
        openConnection()
        with conn.cursor() as cur:
            # select first
            sql = """ SELECT * FROM discord_userinfo 
                      WHERE `user_id` = %s """
            cur.execute(sql, (user_id,))
            result = cur.fetchone()
            return result
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return None


def sql_userinfo_locked(user_id: str, locked: str, locked_reason: str, locked_by: str):
    global conn
    if locked.upper() not in ["YES", "NO"]:
        return
    try:
        openConnection()
        with conn.cursor() as cur:
            # select first
            sql = """ SELECT `user_id` FROM discord_userinfo 
                      WHERE `user_id` = %s """
            cur.execute(sql, (user_id,))
            result = cur.fetchone()
            if result is None:
                sql = """ INSERT INTO `discord_userinfo` (`user_id`, `locked`, `locked_reason`, `locked_by`, `locked_date`)
                      VALUES (%s, %s, %s, %s, %s) """
                cur.execute(sql, (user_id, locked.upper(), locked_reason, locked_by, int(time.time())))
                conn.commit()
            else:
                sql = """ UPDATE `discord_userinfo` SET `locked`= %s, `locked_reason` = %s, `locked_by` = %s, `locked_date` = %s
                      WHERE `user_id` = %s """
                cur.execute(sql, (locked.upper(), locked_reason, locked_by, int(time.time()), user_id))
                conn.commit()
            return True
    except Exception as e:
        traceback.print_exc(file=sys.stdout)


# Steal from https://nitratine.net/blog/post/encryption-and-decryption-in-python/
def encrypt_string(to_encrypt: str):
    key = (config.encrypt.key).encode()

    # Encrypt
    message = to_encrypt.encode()
    f = Fernet(key)
    encrypted = f.encrypt(message)
    return encrypted.decode()


def decrypt_string(decrypted: str):
    key = (config.encrypt.key).encode()

    # Decrypt
    f = Fernet(key)
    decrypted = f.decrypt(decrypted.encode())
    return decrypted.decode()
