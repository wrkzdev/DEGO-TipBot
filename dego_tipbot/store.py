from typing import List
from datetime import datetime
import time
import json

import sys
sys.path.append("..")
import wallet, daemonrpc_client
from config import config
import asyncio

# MySQL
import pymysql
conn = None

# OpenConnection
def openConnection():
    global conn
    try:
        if(conn is None):
            conn = pymysql.connect(config.mysql.host, user=config.mysql.user, passwd=config.mysql.password, db=config.mysql.db, connect_timeout=5)
        elif (not conn.open):
            conn = pymysql.connect(config.mysql.host, user=config.mysql.user, passwd=config.mysql.password, db=config.mysql.db, connect_timeout=5)
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
        print(e)
    finally:
        conn.close()


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
        print(e)
    finally:
        conn.close()


async def sql_register_user(userID):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT user_id, balance_wallet_address, user_wallet_address FROM dego_user WHERE `user_id`=%s LIMIT 1 """
            cur.execute(sql, (userID))
            result = cur.fetchone()
            if result is None:
                balance_address = await wallet.register()
                if (balance_address is None):
                   print('Internal error during call register wallet-api')
                   return
                else:
                   walletStatus = daemonrpc_client.getWalletStatus()
                   if (walletStatus is None):
                       print('Can not reach wallet-api during sql_register_user')
                       chainHeight = 0
                   else:
                       chainHeight = int(walletStatus['blockCount']) # reserve 20
                   sql = """ INSERT INTO dego_user (`user_id`, `balance_wallet_address`, `balance_wallet_address_ts`, `balance_wallet_address_ch`, `privateSpendKey`) 
                             VALUES (%s, %s, %s, %s, %s) """
                   cur.execute(sql, (str(userID), balance_address['address'], int(time.time()), chainHeight, balance_address['privateSpendKey'], ))
                   conn.commit()
                   result2 = {}
                   result2['balance_wallet_address'] = balance_address
                   result2['user_wallet_address'] = ''
                   return result2
            else:
                result2 = {}
                result2['user_id'] = result[0]
                result2['balance_wallet_address'] = result[1]
                if 2 in result:
                    result2['user_wallet_address'] = result[2]
                return result2
    except Exception as e:
        print(e)
    finally:
        conn.close()


async def sql_update_user(userID, user_wallet_address):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT user_id, user_wallet_address, balance_wallet_address FROM dego_user WHERE `user_id`=%s LIMIT 1 """
            cur.execute(sql, (userID))
            result = cur.fetchone()
            if result is None:
                balance_address = await wallet.register()
                if (balance_address is None):
                   print('Internal error during call register wallet-api')
                   return
            else:
                sql = """ UPDATE dego_user SET user_wallet_address=%s WHERE user_id=%s """
                cur.execute(sql, (user_wallet_address, str(userID),))
                conn.commit()
                result2 = {}
                result2['balance_wallet_address'] = result[2]
                result2['user_wallet_address'] = user_wallet_address
                return result2
    except Exception as e:
        print(e)
    finally:
        conn.close()


def sql_get_userwallet(userID):
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
                userwallet = {}
                userwallet['balance_wallet_address'] = result[1]
                if result[2]:
                    userwallet['user_wallet_address'] = result[2]
                if result[3]:
                    userwallet['balance_wallet_address_ts'] = result[3]
                if result[4]:
                    userwallet['balance_wallet_address_ch'] = result[4]
                if result[5]:
                    userwallet['lastOptimize'] = result[5]
                sql = """ SELECT balance_wallet_address, actual_balance, locked_balance, lastUpdate FROM dego_walletapi 
                          WHERE `balance_wallet_address`=%s LIMIT 1 """
                cur.execute(sql, (userwallet['balance_wallet_address'],))
                result2 = cur.fetchone()
                if result2:
                    userwallet['actual_balance'] = int(result2[1])
                    userwallet['locked_balance'] = int(result2[2])
                    userwallet['lastUpdate'] = int(result2[3])
                else:
                    userwallet['actual_balance'] = 0
                    userwallet['locked_balance'] = 0
                return userwallet
    except Exception as e:
        print(e)
    finally:
        conn.close()


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
        print(e)
    finally:
        conn.close()


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
        print(e)
    finally:
        conn.close()
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
        print(e)
    finally:
        conn.close()
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
                Expense = result[0]
            else:
                Expense = 0

            sql = """ SELECT SUM(amount) AS Income FROM dego_mv_tx WHERE `to_userid`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                Income = result[0]
            else:
                Income = 0

            sql = """ SELECT SUM(amount) AS DepositWallet FROM dego_deposit_towallet WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                DepositWallet = result[0]
            else:
                DepositWallet = 0

            sql = """ SELECT SUM(amount) AS TxExpense FROM dego_external_tx WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                TxExpense = result[0]
            else:
                TxExpense = 0

            sql = """ SELECT SUM(fee) AS TxWithdraw FROM dego_external_tx WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                TxWithdraw = result[0]
            else:
                TxWithdraw = 0

            sql = """ SELECT SUM(fee) AS IntFeeExpense FROM dego_deposit_towallet WHERE `user_id`=%s """
            cur.execute(sql, userID)
            result = cur.fetchone()
            if result:
                IntFeeExpense = result[0]
            else:
                IntFeeExpense = 0

            balance = {}
            balance['Expense'] = Expense or 0
            balance['Income'] = Income or 0
            balance['DepositWallet'] = DepositWallet or 0
            balance['TxExpense'] = TxExpense or 0
            balance['TxWithdraw'] = TxWithdraw or 0
            balance['IntFeeExpense'] = IntFeeExpense or 0
            print(balance)
            balance['Adjust'] = int(balance['DepositWallet'] + balance['Income'] - balance['Expense'] - balance['TxExpense'] - balance['TxWithdraw'] - balance['IntFeeExpense'])
            print(balance['Adjust'])
            return balance
    except Exception as e:
        print(e)
    finally:
        conn.close()
    return False


async def sql_send_tip_Ex(user_from: str, address_to: str, amount: int, txtype: str):
    if txtype.upper() not in ["SEND", "WITHDRAW"]:
        return None
    user_from_wallet = sql_get_userwallet(user_from)
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
                print(e)
            finally:
                conn.close()
            return tx_hash
    else:
        return None


async def sql_send_tip_Ex_id(user_from: str, address_to: str, amount: int, paymentid: str, txtype: str):
    if txtype.upper() not in ["SEND", "WITHDRAW"]:
        return None
    user_from_wallet = sql_get_userwallet(user_from)
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
                print(e)
            finally:
                conn.close()
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
                    tag = {}
                    tag['tag_id'] = result[0]
                    tag['tag_desc'] = result[1]
                    tag['date_added'] = result[2]
                    tag['tag_serverid'] = result[3]
                    tag['added_byname'] = result[4]
                    tag['added_byuid'] = result[5]
                    tag['num_trigger'] = result[6]
                    sql = """ UPDATE dego_tag SET num_trigger=num_trigger+1 WHERE tag_serverid = %s AND tag_id=%s """
                    cur.execute(sql, (server_id, tag_id,))
                    conn.commit()
                    return tag
    except Exception as e:
        print(e)
    finally:
        conn.close()


def sql_tag_by_server_add(server_id: str, tag_id: str, tag_desc: str, added_byname: str, added_byuid: str):
    try:
        openConnection()
        with conn.cursor() as cur:
            sql = """ SELECT COUNT(tag_serverid) FROM dego_tag WHERE tag_serverid=%s """
            cur.execute(sql, (server_id,))
            counting = cur.fetchone()
            if counting:
                if counting[0] > 20:
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
        print(e)
    finally:
        conn.close()


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
        print(e)
    finally:
        conn.close()


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
        print(e)
    finally:
        conn.close()


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
                    if int(item[0]) not in list_talker:
                        list_talker.append(int(item[0]))
            return list_talker
    except Exception as e:
        print(e)
    finally:
        conn.close()
    return None


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
                ignorelist.append(row[0])
            return ignorelist
    except Exception as e:
        print(e)
    finally:
        conn.close()


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
            print(e)
        finally:
            conn.close()
    elif onoff == "ON":
        try:
            openConnection()
            with conn.cursor() as cur:
                sql = """ DELETE FROM `bot_tipnotify_user` WHERE `user_id` = %s """
                cur.execute(sql, str(user_id))
                conn.commit()
        except Exception as e:
            print(e)
        finally:
            conn.close()