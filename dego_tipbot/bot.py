import click
import time, timeago, json

import discord
from discord.ext import commands
from discord.ext.commands import Bot, AutoShardedBot
from discord.utils import get

import sys
sys.path.append("..")
import store, daemonrpc_client, addressvalidation
from config import config

## regex
import re
## reaction
from discord.utils import get
from datetime import datetime
import math

# Setting up asyncio to use uvloop if possible, a faster implementation on the event loop
import asyncio

# CapEtn: 386761001808166912
# Need to put some
MAINTENANCE_OWNER = [ 386761001808166912 ] ## list owner
IS_MAINTENANCE = int(config.maintenance)
ENABLE_WITHSEND = int(config.withdrawsend)
IGNORE_TIP_SERVER = [ 460755304863498250 ]
# 460755304863498250: WrkzCoin Server
LOG_CHAN = 572686071771430922

COIN_DIGITS = config.coin.decimal
COIN_REPR = config.coin.name
BOT_INVITELINK = 'https://discordapp.com/oauth2/authorize?client_id=525612379187314688&scope=bot'

MESSAGE_HISTORY_MAX = 20  # message history to store
MESSAGE_HISTORY_TIME = 60  # duration max to put to DB
MESSAGE_HISTORY_LIST = []
MESSAGE_HISTORY_LAST = 0

## Get them from https://emojipedia.org
EMOJI_MONEYBAG = "\U0001F4B0"
EMOJI_ERROR = "\u274C"
EMOJI_TICK = "\u2705"
EMOJI_WARNING = "\u26A0"
EMOJI_SPEAK = "\U0001F4AC"
EMOJI_STOPSIGN = "\U0001F6D1"
EMOJI_PURSE = "\U0001F45B"
EMOJI_HOURGLASS = "\u231B"

NOTIFICATION_OFF_CMD = 'Type: `.notifytip off` to turn off this DM notification.'

bot_description = f"Tip {COIN_REPR} to other users on your server."
bot_help_register = "Register or change your deposit address."
bot_help_info = "Get your account's info."
bot_help_withdraw = f"Withdraw {COIN_REPR} from your balance."
bot_help_balance = f"Check your {COIN_REPR} balance."
bot_help_botbalance = f"Check (only) bot {COIN_REPR} balance."
bot_help_donate = f"Donate {COIN_REPR} to a Bot Owner."
bot_help_tip = f"Give {COIN_REPR} to a user from your balance."
bot_help_tipall = f"Spread a tip amount of {COIN_REPR} to all online members."
bot_help_send = f"Send {COIN_REPR} to a {COIN_REPR} address from your balance (supported integrated address)."
bot_help_address = f"Check {COIN_REPR} address | Generate {COIN_REPR} integrated address `.address` more info."
bot_help_paymentid = "Make a random payment ID with 64 chars length."
bot_help_stats = f"Show summary {COIN_REPR}: height, difficulty, etc."
bot_help_tag = "Display a description or a link about what it is. (-add|-del) requires permission `manage_channels`"
bot_help_notifytip = "Toggle notify tip notification from bot ON|OFF"

bot = AutoShardedBot(command_prefix='.', case_insensitive=True, dm_help = True, dm_help_threshold = 100)

@bot.event
async def on_ready():
    print('Ready!')
    print("Hello, I am DEGO TipBot!")
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    print("Guilds: {}".format(len(bot.guilds)))
    print("Users: {}".format(sum([x.member_count for x in bot.guilds])))
    game = discord.Game(name="Tipping Dego")
    await bot.change_presence(status=discord.Status.online, activity=game)


@bot.event
async def on_shard_ready(shard_id):
    print(f'Shard {shard_id} connected')


@bot.event
async def on_message(message):
    global MESSAGE_HISTORY_LIST, MESSAGE_HISTORY_TIME, MESSAGE_HISTORY_MAX, MESSAGE_HISTORY_LAST
    if len(MESSAGE_HISTORY_LIST) > 0:
        if len(MESSAGE_HISTORY_LIST) > MESSAGE_HISTORY_MAX or time.time() - MESSAGE_HISTORY_LAST > MESSAGE_HISTORY_TIME:
            # add to DB
            numb_message = store.sql_add_messages(MESSAGE_HISTORY_LIST)
            print('Added number of messages: ' + str(numb_message))
            #print(MESSAGE_HISTORY_LIST)
            MESSAGE_HISTORY_LIST = []
            MESSAGE_HISTORY_LAST == 0
            #print('reset number of message')
    if isinstance(message.channel, discord.DMChannel) == False and message.author.bot == False and len(message.content) > 0 and message.author != bot.user:
        MESSAGE_HISTORY_LIST.append((str(message.guild.id), message.guild.name, str(message.channel.id), message.channel.name, 
            str(message.author.id), message.author.name, str(message.id), int(time.time())))
        if MESSAGE_HISTORY_LAST == 0:
            MESSAGE_HISTORY_LAST = int(time.time())

    if isinstance(message.channel, discord.DMChannel):
        pass
    else:
        if message.guild.id in IGNORE_TIP_SERVER:
            return

    # do some extra stuff here
    if int(message.author.id) in MAINTENANCE_OWNER:
        # It is better to set bot to MAINTENANCE mode before restart or stop
        args = message.content.split(" ")
        if len(args)==2:
            if args[0].upper() == "MAINTENANCE":
                if args[1].upper()=="ON":
                    IS_MAINTENANCE = 1
                    await message.author.send('Maintenance ON, `maintenance off` to turn it off.')
                    return
                else:
                    IS_MAINTENANCE = 0
                    await message.author.send('Maintenance OFF, `maintenance on` to turn it off.')
                    return
    # Do not remove this, otherwise, command not working.
    ctx = await bot.get_context(message)
    await bot.invoke(ctx)


@bot.command(pass_context=True, name='info', aliases=['wallet', 'tipjar'], help=bot_help_info)
async def info(ctx):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    user = store.sql_register_user(str(ctx.message.author.id))
    wallet = store.sql_get_userwallet(str(ctx.message.author.id))
    if wallet is None:
        await ctx.message.author.send('Internal Error for `.info`')
        return
    if 'user_wallet_address' in wallet:
        await ctx.message.add_reaction(EMOJI_TICK)
        await ctx.message.author.send(
            f'**[ACCOUNT INFO]**\n\n'
            f'{EMOJI_PURSE} Deposit Address: `'+wallet['balance_wallet_address']+'`\n'
            f'{EMOJI_MONEYBAG} Registered Wallet: `'+wallet['user_wallet_address']+'`')
    else:
        await ctx.message.add_reaction(EMOJI_WARNING)
        await ctx.message.author.send(
            f'**[ACCOUNT INFO]**\n\n'
            f'{EMOJI_PURSE} Deposit Address: `'+wallet['balance_wallet_address']+'`\n'
            f'{EMOJI_MONEYBAG} Registered Wallet: `NONE, Please register.`\n')
    return


@bot.command(pass_context=True, name='balance', aliases=['bal'], help=bot_help_balance)
async def balance(ctx):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    # Get wallet status
    walletStatus = daemonrpc_client.getWalletStatus()
    if walletStatus is None:
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Wallet service hasn\'t sync properly.')
        return
    else:
        #print(walletStatus)
        localDaemonBlockCount = int(walletStatus['blockCount'])
        networkBlockCount = int(walletStatus['knownBlockCount'])
        if (networkBlockCount-localDaemonBlockCount) >= 20:
            ## if height is different by 50
            t_percent = '{:,.2f}'.format(truncate(localDaemonBlockCount/networkBlockCount*100,2))
            t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
            t_networkBlockCount = '{:,}'.format(networkBlockCount)
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.message.author.send(
                                    f'{EMOJI_STOPSIGN} Wallet service hasn\'t sync fully with network or being re-sync. More info:\n```'
                                    f'networkBlockCount:     {t_networkBlockCount}\n'
                                    f'localDaemonBlockCount: {t_localDaemonBlockCount}\n'
                                    f'Progress %:            {t_percent}\n```'
                                    )
            return
        else:
            pass
    # End of wallet status

    user = store.sql_register_user(str(ctx.message.author.id))
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))
    wallet = store.sql_get_userwallet(ctx.message.author.id)
    #print(wallet)
    #print(userdata_balance)
    if 'lastUpdate' in wallet:
        await ctx.message.add_reaction(EMOJI_TICK)
        try:
            update = datetime.fromtimestamp(int(wallet['lastUpdate'])).strftime('%Y-%m-%d %H:%M:%S')
            ago = timeago.format(update, datetime.now())
            print(ago)
        except:
            pass
    balance_actual = '{:,.2f}'.format((wallet['actual_balance']+int(userdata_balance['Adjust'])) / COIN_DIGITS)
    balance_locked = '{:,.2f}'.format(wallet['locked_balance'] / COIN_DIGITS)
    await ctx.message.author.send('**[YOUR BALANCE]**\n\n'
        f'{EMOJI_MONEYBAG} Available: {balance_actual} '
        f'{COIN_REPR}\n'
        f'{EMOJI_HOURGLASS} Pending: {balance_locked} '
        f'{COIN_REPR}\n')
    if ago:
        await ctx.message.author.send(f'{EMOJI_HOURGLASS} Last update: {ago}')


@bot.command(pass_context=True, aliases=['botbal'], help=bot_help_botbalance)
async def botbalance(ctx, member: discord.Member=None):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    if member is None:
        user = store.sql_register_user(str(bot.user.id))
        wallet = store.sql_get_userwallet(bot.user.id)
        userdata_balance = store.sql_adjust_balance(str(bot.user.id))
        depositAddress = wallet['balance_wallet_address']
        balance_actual = '{:,.2f}'.format((wallet['actual_balance']+int(userdata_balance['Adjust'])) / COIN_DIGITS)
        balance_locked = '{:,.2f}'.format(wallet['locked_balance'] / COIN_DIGITS)
        await ctx.send(
            f'**[MY BALANCE]**\n\n'
            f'{EMOJI_PURSE} Deposit Address: `{depositAddress}`\n'
            f'{EMOJI_MONEYBAG} Available: {balance_actual} '
            f'{COIN_REPR}\n'
            f'{EMOJI_HOURGLASS} Pending: {balance_locked} '
            f'{COIN_REPR}\n'
            '**This is bot\'s tipjar address. Do not deposit here unless you want to deposit to this bot.**')
        return
    if member.bot == False:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await bctx.message.author.send('Only for bot!!')
        return
    else:
        user = store.sql_register_user(str(member.id))
        wallet = store.sql_get_userwallet(member.id)
        userdata_balance = store.sql_adjust_balance(str(member.id))
        balance_actual = '{:,.2f}'.format((wallet['actual_balance']+int(userdata_balance['Adjust'])) / COIN_DIGITS)
        balance_locked = '{:,.2f}'.format(wallet['locked_balance'] / COIN_DIGITS)
        depositAddress = wallet['balance_wallet_address']
        await ctx.send(
            f'**[INFO BOT {member.name}\'s BALANCE]**\n\n'
            f'{EMOJI_PURSE} Deposit Address: `{depositAddress}`\n'
            f'{EMOJI_MONEYBAG} Available: {balance_actual} '
            f'{COIN_REPR}\n'
            f'{EMOJI_HOURGLASS} Pending: {balance_locked} '
            f'{COIN_REPR}\n'
            '**This is bot\'s tipjar address. Do not deposit here unless you want to deposit to this bot.**')
        return


@bot.command(pass_context=True, name='register', aliases=['registerwallet', 'reg', 'updatewallet'], help=bot_help_register)
async def register(ctx, wallet_address: str):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    user_id = ctx.message.author.id
    user = store.sql_get_userwallet(ctx.message.author.id)
    if user:
        existing_user = user
        pass

    valid_address = addressvalidation.validate_address(wallet_address)
    if valid_address is None:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Invalid address:\n'
                        f'`{wallet_address}`')
        return

    if (valid_address!=wallet_address) :
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Invalid address:\n'
                        f'`{wallet_address}`')
        return

    # if they want to register with tipjar address
    try:
        if user['balance_wallet_address'] == wallet_address:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.author.send(
                            f'{EMOJI_STOPSIGN} You can not register with your tipjar\'s address.\n'
                            f'`{wallet_address}`')
            return
        else:
            pass
    except Exception as e:
        await ctx.message.add_reaction(EMOJI_ERROR)
        print('Error during register user address:'+str(e))
        return
        
    if 'user_wallet_address' in existing_user:
        prev_address = existing_user['user_wallet_address']
        store.sql_update_user(user_id, wallet_address)
        if prev_address:
            await ctx.message.add_reaction(EMOJI_TICK)
            await ctx.message.author.send(
                f'Your withdraw address has been changed from:\n'
                f'`{prev_address}`\n to\n '
                f'`{wallet_address}`')
            return
        pass
    else:
        user = store.sql_update_user(user_id, wallet_address)
        await ctx.message.add_reaction(EMOJI_TICK)
        await ctx.message.author.send(
                               'You have been registered a withdraw address.\n'
                               'You can use `.withdraw AMOUNT` anytime.')
        return


@bot.command(pass_context=True, help=bot_help_withdraw)
async def withdraw(ctx, amount: str):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    # Check if withdraw / send enable
    if ENABLE_WITHSEND == 0:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End withdraw / send

    botLogChan = bot.get_channel(id=LOG_CHAN)
    # Check flood of tip
    floodTip = store.sql_get_countLastTx(ctx.message.author.id, config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send(f'{ctx.message.author.name} / {ctx.message.author.id} reached max. TX threshold. Currently halted: `.withdraw`')
        return
    elif floodTip >= config.floodTip - 2:
        await botLogChan.send(f'{ctx.message.author.name} / {ctx.message.author.id} nearly reached max. TX threshold. Currently doing: `.withdraw`')
        pass
    else:
        pass
    # End of Check flood of tip

    amount = amount.replace(",", "")

    try:
        amount = float(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid amount.')
        return

    user = store.sql_get_userwallet(str(ctx.message.author.id))
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))
    real_amount = int(amount * COIN_DIGITS)

    if not user['user_wallet_address']:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
            f'You do not have a withdrawal address, please use '
            f'`.register <wallet_address>` to register.')
        return
    # This is important because it needs to check tipping and other expense.
    if real_amount + config.tx_fee >= user['actual_balance'] + int(userdata_balance['Adjust']):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                               f'{EMOJI_STOPSIGN} Insufficient balance to withdraw '
                               f'{real_amount / COIN_DIGITS:,.2f} '
                               f'{COIN_REPR}.')
        return

    if real_amount > config.max_tx_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Transaction cannot be bigger than '
                        f'{config.max_tx_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}')
        return
    elif real_amount < config.min_tx_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Transaction cannot be lower than '
                        f'{config.min_tx_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}')
        return

    # Get wallet status
    walletStatus = daemonrpc_client.getWalletStatus()
    if walletStatus is None:
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Wallet service hasn\'t sync properly.')
        return
    else:
        localDaemonBlockCount = int(walletStatus['blockCount'])
        networkBlockCount = int(walletStatus['knownBlockCount'])
        if (networkBlockCount - localDaemonBlockCount) >= 20:
            t_percent = '{:,.2f}'.format(truncate(localDaemonBlockCount/networkBlockCount*100,2))
            t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
            t_networkBlockCount = '{:,}'.format(networkBlockCount)
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.message.author.send(
                                    f'{EMOJI_STOPSIGN} Wallet service hasn\'t sync fully with network or being re-sync. More info:\n```'
                                    f'networkBlockCount:     {t_networkBlockCount}\n'
                                    f'localDaemonBlockCount: {t_localDaemonBlockCount}\n'
                                    f'Progress %:            {t_percent}\n```'
                                    )
            return
        else:
            pass
    # End of wallet status

    withdraw = None
    try:
        withdraw = store.sql_send_tip_Ex(str(ctx.message.author.id), user['user_wallet_address'], real_amount, "WITHDRAW")
    except Exception as e:
        print(e)
    if withdraw:
        store.sql_update_some_balances([user['balance_wallet_address']])
        await ctx.message.add_reaction(EMOJI_MONEYBAG)
        await botLogChan.send(f'A user successfully executed `.withdraw {real_amount / COIN_DIGITS:,.2f} {COIN_REPR}`.')
        await ctx.message.author.send(
            f'{EMOJI_MONEYBAG} You have withdrawn {real_amount / COIN_DIGITS:,.2f} '
            f'{COIN_REPR}.\n'
            f'Transaction hash: `{withdraw}`')
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await botLogChan.send(f'A user failed to `.withdraw` amount `{real_amount / COIN_DIGITS:,.2f} {COIN_REPR}`')
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Internal Error. Please report.')
        return


@bot.command(pass_context=True, help=bot_help_donate)
async def donate(ctx, amount: str):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    botLogChan = bot.get_channel(id=LOG_CHAN)
    amount = amount.replace(",", "")
    try:
        amount = float(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid amount.')
        return

    real_amount = int(amount * COIN_DIGITS)
    user_from = store.sql_get_userwallet(ctx.message.author.id)
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))

    if real_amount > user_from['actual_balance'] + int(userdata_balance['Adjust']):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Insufficient balance to donate '
                        f'{real_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    if real_amount > config.max_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Transaction cannot be bigger than '
                        f'{config.max_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')

        return

    tip = None
    try:
        # sql_mv_tx_single(user_from: str, user_name: str, to_user: str, server_id: str, servername: str, messageid: str, amount: int, tiptype: str):
        if isinstance(ctx.channel, discord.DMChannel):
            tip = store.sql_mv_tx_single(str(ctx.message.author.id), str(ctx.message.author.name), "DONATE", "DM",  "DM", str(ctx.message.id), real_amount, "DONATE")
        else:
            tip = store.sql_mv_tx_single(str(ctx.message.author.id), str(ctx.message.author.name), "DONATE", str(ctx.guild.id),  str(ctx.guild.name), str(ctx.message.id), real_amount, "DONATE")
    except Exception as e:
        print(e)
    if tip:
        await ctx.message.add_reaction(EMOJI_MONEYBAG)
        await botLogChan.send(f'A user has donated amount `{real_amount / COIN_DIGITS:,.2f} {COIN_REPR}`.')
        DonateAmount = '{:,.2f}'.format(real_amount / COIN_DIGITS)
        await ctx.message.author.send(
                        f'{EMOJI_MONEYBAG} TipBot got donation: {DonateAmount} '
                        f'{COIN_REPR} '
                        f'\n'
                        f'Thank you.')
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Thank you. Can not deliver TX right now. Try again soon.')
        return


@bot.command(pass_context=True, help=bot_help_notifytip)
async def notifytip(ctx, onoff: str):
    if onoff.upper() not in ["ON", "OFF"]:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send('You need to use only `ON` or `OFF`.')
        return

    onoff = onoff.upper()
    notifyList = store.sql_get_tipnotify()
    if onoff == "ON":
        if str(ctx.message.author.id) in notifyList:
            store.sql_toggle_tipnotify(str(ctx.message.author.id), "ON")
            await ctx.send('OK, you will get all notification when tip.')
            return
        else:
            await ctx.send('You already have notification ON by default.')
            return
    elif onoff == "OFF":
        if str(ctx.message.author.id) in notifyList:
            await ctx.send('You already have notification OFF.')
            return
        else:
            store.sql_toggle_tipnotify(str(ctx.message.author.id), "OFF")
            await ctx.send('OK, you will not get any notification when anyone tips.')
            return


@bot.command(pass_context=True, help=bot_help_tip)
async def tip(ctx, amount: str, *args):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    botLogChan = bot.get_channel(id=LOG_CHAN)
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f'{EMOJI_STOPSIGN} This command can not be in private.')
        return

    amount = amount.replace(",", "")

    if len(ctx.message.mentions) == 0:
        # Use how time.
        if len(args) >= 2:
            time_given = None
            if args[0].upper() == "LAST" or args[1].upper() == "LAST":
                time_string = ctx.message.content.lower().split("last",1)[1].strip()
                time_second = None
                try:
                    time_string = time_string.replace("years", "y")
                    time_string = time_string.replace("yrs", "y")
                    time_string = time_string.replace("yr", "y")
                    time_string = time_string.replace("year", "y")
                    time_string = time_string.replace("months", "mon")
                    time_string = time_string.replace("month", "mon")
                    time_string = time_string.replace("mons", "mon")
                    time_string = time_string.replace("weeks", "w")
                    time_string = time_string.replace("week", "w")
                    time_string = time_string.replace("days", "d")
                    time_string = time_string.replace("day", "d")
                    time_string = time_string.replace("hours", "h")
                    time_string = time_string.replace("minutes", "mn")
                    time_string = time_string.replace("hr", "h")
                    time_string = time_string.replace("hrs", "h")
                    time_string = time_string.replace("mns", "mn")
                    mult = {'y': 12*30*24*60*60, 'mon': 30*24*60*60, 'w': 7*24*60*60, 'd': 24*60*60, 'h': 60*60, 'mn': 60}
                    time_second = sum(int(num) * mult.get(val, 1) for num, val in re.findall('(\d+)(\w+)', time_string))
                except Exception as e:
                    print(e)
                    await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid time given. Please use this example: `.tip 1,000 last 5h 12mn`')
                    return
                try:
                    time_given = int(time_second)
                except ValueError:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.message.author.send(f'{EMOJI_STOPSIGN} Invalid time given check.')
                    return
                print('time_given:'+str(time_given))
                if time_given:
                    if time_given < 5*60 or time_given > 5*365*24*60*60:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Please try time inteval between 5 minutes to 5 years.')
                        return
                    else:
                        message_talker = store.sql_get_messages(str(ctx.message.guild.id), str(ctx.message.channel.id), time_given)
                        if len(message_talker) == 0:
                            await ctx.message.add_reaction(EMOJI_ERROR)
                            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} There is no active talker in such period.')
                            return
                        else:
                            #print(message_talker)
                            await _tip_talker(ctx, amount, message_talker)
                            return
            else:
                await ctx.send(f'{EMOJI_RED_NO} You need at least one person to tip to.')
                return
        else:
            await ctx.send(f'{EMOJI_RED_NO} You need at least one person to tip to.')
            return
    elif len(ctx.message.mentions) > 1:
        await _tip(ctx, amount)
        return
    elif len(ctx.message.mentions) == 1:
        member = ctx.message.mentions[0]

    user_from = store.sql_get_userwallet(ctx.message.author.id)
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))
    user_to = store.sql_register_user(member.id)

    try:
        amount = float(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid amount.')
        return

    real_amount = int(amount * COIN_DIGITS)

    if real_amount > user_from['actual_balance'] + int(userdata_balance['Adjust']):
        #print('Insufficient balance to send tip')
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Insufficient balance to send tip of '
                        f'{real_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR} to {member.mention}.')
        return

    if real_amount > config.max_mv_amount:
        #print('Transaction cannot be bigger than')
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be bigger than '
                        f'{config.max_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_mv_amount:
        #print('Transaction cannot be smaller than')
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    notifyList = store.sql_get_tipnotify()
    tip = None
    try:
        # sql_mv_tx_single(user_from: str, user_name: str, to_user: str, server_id: str, servername: str, messageid: str, amount: int, tiptype: str)
        tip = store.sql_mv_tx_single(str(ctx.message.author.id), str(ctx.message.author.name), str(member.id), str(ctx.guild.id),  str(ctx.guild.name), str(ctx.message.id), real_amount, "TIP")
    except Exception as e:
        print(e)
    if tip:
        tipAmount = '{:,.2f}'.format(real_amount / COIN_DIGITS)
        await ctx.message.add_reaction(EMOJI_MONEYBAG)
        if str(ctx.message.author.id) not in notifyList:
            try:
                await ctx.message.author.send(
                                f'{EMOJI_MONEYBAG} Tip of {tipAmount} '
                                f'{COIN_REPR} '
                                f'was sent to `{member.name}` '
                                f'in server: `{ctx.guild.name}`')
            except Exception as e:
                # add user to notifyList
                print('Adding: ' + str(ctx.message.author.id) + ' not to receive DM tip')
                store.sql_toggle_tipnotify(str(ctx.message.author.id), "OFF")
                print(e)
        if str(member.id) not in notifyList:
            try:
                await member.send(
                            f'{EMOJI_MONEYBAG} You got a tip of {tipAmount} '
                            f'{COIN_REPR} from `{ctx.message.author.name}` '
                            f'in server  hash: `{ctx.guild.name}`\n'
                            f'{NOTIFICATION_OFF_CMD}')
            except Exception as e:
                # add user to notifyList
                print('Adding: ' + str(member.id) + ' not to receive DM tip')
                store.sql_toggle_tipnotify(str(member.id), "OFF")
                print(e)
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Can not deliver tipping right now. Try again soon.')
        return


@bot.command(pass_context=True, help=bot_help_tipall)
async def tipall(ctx, amount: str):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    botLogChan = bot.get_channel(id=LOG_CHAN)
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f'{EMOJI_STOPSIGN} This command can not be in private.')
        return

    amount = amount.replace(",", "")
    try:
        amount = float(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid amount.')
        return

    real_amount = int(amount * COIN_DIGITS)
    listMembers = [member for member in ctx.guild.members if member.status != discord.Status.offline]
  
    memids = []  ## list of member ID
    for member in listMembers:
        if ctx.message.author.id != member.id:
            if (str(member.status) != 'offline'):
                if member.bot == False:
                    memids.append(str(member.id))

    amountDiv = round(real_amount / len(memids), 2)
    if (real_amount / len(memids)) < config.min_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be smaller than '
                       f'{config.min_mv_amount:,.2f} '
                       f'{COIN_REPR} for each member. You need at least {len(memids) * config.min_mv_amount:,.2f} {COIN_REPR}.')
        return

    user_from = store.sql_get_userwallet(str(ctx.message.author.id))
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))
    if real_amount > user_from['actual_balance'] + int(userdata_balance['Adjust']):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Insufficient balance to spread tip of '
                        f'{real_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    if real_amount > config.max_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be bigger than '
                        f'{config.max_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    elif (real_amount / len(memids)) < config.min_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR} for each member. You need at least {len(memids) * config.min_mv_amount / COIN_DIGITS:,.2f} {COIN_REPR}.')
        return

    notifyList = store.sql_get_tipnotify()
    tips = None
    try:
        # sql_mv_tx_multiple(user_from: str, user_name: str, user_tos, server_id: str, servername: str, messageid: str, amount_each: int, tiptype: str)
        tips = store.sql_mv_tx_multiple(str(ctx.message.author.id), str(ctx.message.author.name), memids, str(ctx.guild.id), str(ctx.guild.name), str(ctx.message.id), amountDiv, "TIPALL")
    except Exception as e:
        print(e)
    if tips:
        await ctx.message.add_reaction(EMOJI_MONEYBAG)
        TotalSpend = '{:,.2f}'.format(real_amount / COIN_DIGITS)
        ActualSpend = int(int(amountDiv) * len(memids))
        ActualSpend_str = '{:,.2f}'.format(ActualSpend / COIN_DIGITS)
        amountDiv_str = '{:,.2f}'.format(int(amountDiv) / COIN_DIGITS)
        if str(ctx.message.author.id) not in notifyList:
            try:
                await ctx.message.author.send(
                                        f'{EMOJI_MONEYBAG} Tip of {TotalSpend} '
                                        f'{COIN_REPR} '
                                        f'was sent spread to ({len(memids)}) members '
                                        f'in server: `{ctx.guild.name}`.\n'
                                        f'Each member got: `{amountDiv_str}{COIN_REPR}`\n'
                                        f'Actual spending: `{ActualSpend_str}{COIN_REPR}`')
            except Exception as e:
                # add user to notifyList
                print('Adding: ' + str(ctx.message.author.id) + ' not to receive DM tip')
                store.sql_toggle_tipnotify(str(ctx.message.author.id), "OFF")
                print(e)
        numMsg = 0
        for member in listMembers:
            if ctx.message.author.id != member.id:
                if str(member.status) != 'offline':
                    if member.bot == False:
                        if str(member.id) not in notifyList:
                            try:
                                await member.send(
                                        f'{EMOJI_MONEYBAG} You got a tip of {amountDiv_str} '
                                        f'{COIN_REPR} from `{ctx.message.author.name} .tipall` '
                                        f'in server: `{ctx.guild.name}`.\n'
                                        f'{NOTIFICATION_OFF_CMD}')
                                numMsg = numMsg + 1
                            except Exception as e:
                                # add user to notifyList
                                print('Adding: ' + str(member.id) + ' not to receive DM tip')
                                store.sql_toggle_tipnotify(str(member.id), "OFF")
                                print(e)
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Can not deliver TX right now. Try again soon.')
        return


@bot.command(pass_context=True, help=bot_help_send)
async def send(ctx, amount: str, CoinAddress: str):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.message.author.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    # Check if withdraw / send enable
    if ENABLE_WITHSEND == 0:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End withdraw / send

    botLogChan = bot.get_channel(id=LOG_CHAN)
    # Check flood of tip
    floodTip = store.sql_get_countLastTx(ctx.message.author.id, config.floodTipDuration)
    if floodTip >= config.floodTip:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Cool down your tip or TX. or increase your amount next time.')
        await botLogChan.send(f'{ctx.message.author.name} / {ctx.message.author.id} reached max. TX threshold. Currently halted: `.send`')
        return
    elif floodTip >= config.floodTip - 2:
        await botLogChan.send(f'{ctx.message.author.name} / {ctx.message.author.id} nearly reached max. TX threshold. Currently doing: `.send`')
        pass
    else:
        pass
    # End of Check flood of tip

    if len(CoinAddress) == int(config.coin.AddrLen):
        valid_address = addressvalidation.validate_address(CoinAddress)
        #print(valid_address)
        if valid_address is None:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.author.send(
                            f'{EMOJI_STOPSIGN} Invalid address:\n'
                            f'`{CoinAddress}`')
            return
        if (valid_address!=CoinAddress) :
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.author.send(
                            f'{EMOJI_STOPSIGN} Invalid address:\n'
                            f'`{CoinAddress}`')
            return
    elif len(CoinAddress) == 185:
        valid_address = addressvalidation.validate_integrated(CoinAddress)
        #print(valid_address)
        if valid_address == 'invalid':
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.message.author.send(
                            f'{EMOJI_STOPSIGN} Invalid integrated address:\n'
                            f'`{CoinAddress}`')
            return
        if len(valid_address) == 2:
            iCoinAddress=CoinAddress
            CoinAddress=valid_address['address']
            paymentid=valid_address['integrated_id']
    elif len(CoinAddress) == int(config.coin.AddrLen) + 64 + 1:
        valid_address = {}
        check_address = CoinAddress.split(".")
        if len(check_address) != 2:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'Invalid {COIN_REPR} address + paymentid')
            return
        else:
            valid_address_str = addressvalidation.validate_address(check_address[0])
            paymentid = check_address[1].strip()
            if valid_address_str is None:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.message.author.send(
                                       f'{EMOJI_STOPSIGN}  Invalid address:\n'
                                       f'`{check_address[0]}`')
                return
            else:
                valid_address['address'] = check_address[0]
            ## Check payment ID
            if len(paymentid) == 64:
                if not re.match(r'[a-zA-Z0-9]{64,}', paymentid.strip()):
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_STOPSIGN}  PaymentID: `{paymentid}`\n'
                                    'Should be in 64 correct format.')
                    return
                else:
                    CoinAddress = valid_address['address']
                    valid_address['integrated_id'] = paymentid
                    iCoinAddress = addressvalidation.make_integrated(CoinAddress, paymentid)['integrated_address']
                    pass
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_STOPSIGN}  PaymentID: `{paymentid}`\n'
                                'Incorrect length')
                return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Invalid address:\n'
                        f'`{CoinAddress}`')
        return

    amount = amount.replace(",", "")

    try:
        amount = float(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid amount.')
        return

    real_amount = int(amount * COIN_DIGITS)
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))
    user_from = store.sql_get_userwallet(ctx.message.author.id)
    if user_from['balance_wallet_address'] == CoinAddress:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} You can not send to your own deposit address.')
        return
    # This is important because it needs to check tipping and other expense.
    if real_amount + config.tx_fee >= user_from['actual_balance'] + int(userdata_balance['Adjust']):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Insufficient balance to send '
                        f'{real_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR} to {CoinAddress}.')

        return

    if real_amount > config.max_tx_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Transaction cannot be bigger than '
                        f'{config.max_tx_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_tx_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.message.author.send(
                        f'{EMOJI_STOPSIGN} Transaction cannot be smaller than '
                        f'{config.min_tx_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')

        return

    # Get wallet status
    walletStatus = daemonrpc_client.getWalletStatus()
    if walletStatus is None:
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Wallet service hasn\'t sync properly.')
        return
    else:
        #print(walletStatus)
        localDaemonBlockCount = int(walletStatus['blockCount'])
        networkBlockCount = int(walletStatus['knownBlockCount'])
        if (networkBlockCount-localDaemonBlockCount) >= 20:
            ## if height is different by 50
            t_percent = '{:,.2f}'.format(truncate(localDaemonBlockCount/networkBlockCount*100,2))
            t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
            t_networkBlockCount = '{:,}'.format(networkBlockCount)
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.message.author.send(
                                    f'{EMOJI_STOPSIGN} Wallet service hasn\'t sync fully with network or being re-sync. More info:\n```'
                                    f'networkBlockCount:     {t_networkBlockCount}\n'
                                    f'localDaemonBlockCount: {t_localDaemonBlockCount}\n'
                                    f'Progress %:            {t_percent}\n```'
                                    )
            return
        else:
            pass
    # End of wallet status

    if len(valid_address) == 2:
        #print(valid_address)
        #print('Process integrate address...')
        tip = None
        try:
            tip = store.sql_send_tip_Ex_id(str(ctx.message.author.id), CoinAddress, real_amount, paymentid, "SEND")
        except Exception as e:
            print(e) 
        if tip:
            store.sql_update_some_balances([user_from['balance_wallet_address']])
            await ctx.message.add_reaction(EMOJI_MONEYBAG)
            await botLogChan.send(f'A user successfully executed `.send {real_amount / COIN_DIGITS:,.2f} {COIN_REPR}` with paymentid.')
            await ctx.message.author.send(
                            f'{EMOJI_MONEYBAG} Amount {real_amount / COIN_DIGITS:,.2f} '
                            f'{COIN_REPR} '
                            f'was sent to `{iCoinAddress}`\n'
                            f'Address: `{CoinAddress}`\n'
                            f'Payment ID: `{paymentid}`\n'
                            f'Transaction hash: `{tip}`')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await botLogChan.send(f'A user failed to `.send` amount `{real_amount / COIN_DIGITS:,.2f} {COIN_REPR}` using paymentid.')
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Internal Error. Please report `.send`.')
            return
    else:
        #print('Process normal address...')
        tip = None
        try:
            tip = store.sql_send_tip_Ex(str(ctx.message.author.id), CoinAddress, real_amount, "SEND")
        except Exception as e:
            print(e)        
        if tip:
            store.sql_update_some_balances([user_from['balance_wallet_address']])
            await ctx.message.add_reaction(EMOJI_MONEYBAG)
            await botLogChan.send(f'A user successfully executed `.send {real_amount / COIN_DIGITS:,.2f} {COIN_REPR}` without paymentid.')
            await ctx.message.author.send(
                            f'{EMOJI_MONEYBAG} Amount {real_amount / COIN_DIGITS:,.2f} '
                            f'{COIN_REPR} '
                            f'was sent to `{CoinAddress}`\n'
                            f'Transaction hash: `{tip}`')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await botLogChan.send(f'A user failed to `.send` amount `{real_amount / COIN_DIGITS:,.2f} {COIN_REPR}` without paymentid.')
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Internal Error. Please report `.send`.')
            return


@bot.command(pass_context=True, name='address', aliases=['addr'], help=bot_help_address)
async def address(ctx, *args):
    if len(args) == 0:
        await ctx.message.add_reaction(EMOJI_TICK)
        await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                        '`.address dg4v9ZRhAbY94UZ9D5URmHcdTvSBvmoxrLRoN7ERJFXTh6VGw3giAL3Ke5vDX65UHaJj2aWXZSsxmCnYraBwAc3M323oeCrSX`\n'
                        'That will check if the address is valid. Integrated address is also supported. '
                        'If integrated address is input, bot will tell you the result of :address + paymentid\n\n'
                        '`.address <coin_address> <paymentid>`\n'
                        'This will generate an integrate address.\n\n')
        return
    if len(args) == 1:
        CoinAddress=args[0]
        if len(CoinAddress) == int(config.coin.AddrLen):
            if not re.match(r'dg[a-zA-Z0-9]{95,}', CoinAddress.strip()):
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_STOPSIGN} Address: `{CoinAddress}`\n'
                                'Checked: Invalid. Should start with dg.')
                return
            else:
                valid_address = addressvalidation.validate_address(CoinAddress)
                if valid_address is None:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_STOPSIGN} Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_TICK)
                    if(valid_address==CoinAddress):
                        await ctx.send(f'Address: `{CoinAddress}`\n'
                                        'Checked: Valid.')
                    return
            return
        elif len(CoinAddress) == int(config.coin.IntAddrLen):
            # Integrated address
            if not re.match(r'dg[a-zA-Z0-9]{183,}', CoinAddress.strip()):
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_STOPSIGN} Integrated Address: `{CoinAddress}`\n'
                                'Checked: Invalid. Should start with dg.')
                return
            else:
                valid_address = addressvalidation.validate_integrated(CoinAddress)
                if valid_address == 'invalid':
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_STOPSIGN} Integrated Address: `{CoinAddress}`\n'
                                    'Checked: Invalid.')
                    return
                if len(valid_address) == 2:
                    await ctx.message.add_reaction(EMOJI_TICK)
                    iCoinAddress=CoinAddress
                    CoinAddress=valid_address['address']
                    paymentid=valid_address['integrated_id']
                    await ctx.send(f'\nIntegrated Address: `{iCoinAddress}`\n\n'
                                    f'Address: `{CoinAddress}`\n'
                                    f'PaymentID: `{paymentid}`')
                    return
                return
        else:
            # incorrect length
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_STOPSIGN} Address: `{CoinAddress}`\n'
                            'Checked: Incorrect length')
            return
    if len(args) == 2:
        # generate integrated address:
        CoinAddress=args[0]
        paymentid=args[1]
        if len(CoinAddress) == int(config.coin.AddrLen):
            if not re.match(r'dg[a-zA-Z0-9]{95,}', CoinAddress.strip()):
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_STOPSIGN} Address: `{CoinAddress}`\n'
                                'Checked: Invalid. Should start with dg.')
                return
            else:
                valid_address = addressvalidation.validate_address(CoinAddress)
                if valid_address is None:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_STOPSIGN} Address: `{CoinAddress}`\n'
                                    'Checked: Incorrect given address.')
                    return
                else:
                    pass
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_STOPSIGN} Address: `{CoinAddress}`\n'
                            'Checked: Incorrect length')
            return
        # Check payment ID
        if len(paymentid) == 64:
            if not re.match(r'[a-zA-Z0-9]{64,}', paymentid.strip()):
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_STOPSIGN} PaymentID: `{paymentid}`\n'
                                'Checked: Invalid. Should be in 64 correct format.')
                return
            else:
                pass
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_STOPSIGN} PaymentID: `{paymentid}`\n'
                            'Checked: Incorrect length')
            return
        # Make integrated address:
        integrated_address=addressvalidation.make_integrated(CoinAddress, paymentid)
        if 'integrated_address' in integrated_address:
            iCoinAddress = integrated_address['integrated_address']
            await ctx.message.add_reaction(EMOJI_TICK)
            await ctx.send(f'\nNew integrated address: `{iCoinAddress}`\n\n'
                            f'Main address: `{CoinAddress}`\n'
                            f'Payment ID: `{paymentid}`\n')
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.send(f'{EMOJI_STOPSIGN} ERROR Can not make integrated address.\n')
            return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send('**[ ADDRESS CHECKING EXAMPLES ]**\n\n'
                       f'`.address {config.coin.DonateAddress}`\n'
                       'That will check if the address is valid. Integrated address is also supported. '
                       'If integrated address is input, bot will tell you the result of :address + paymentid\n\n'
                       '`.address <coin_address> <paymentid>`\n'
                       'This will generate an integrate address.\n\n')
        return


@bot.command(pass_context=True, name='paymentid', aliases=['payid'], help=bot_help_paymentid)
async def paymentid(ctx):
    paymentid = addressvalidation.paymentid()
    await ctx.message.add_reaction(EMOJI_TICK)
    await ctx.send('**[ RANDOM PAYMENT ID ]**\n'
                    f'`{paymentid}`\n')
    return


@bot.command(pass_context=True, aliases=['diff', 'height', 'stat'], help=bot_help_stats)
async def stats(ctx):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    gettopblock = await daemonrpc_client.gettopblock()
    #print(gettopblock)
    walletStatus = daemonrpc_client.getWalletStatus()
    if gettopblock:
        blockfound = datetime.utcfromtimestamp(int(gettopblock['block_header']['timestamp'])).strftime("%Y-%m-%d %H:%M:%S")
        ago = str(timeago.format(blockfound, datetime.utcnow()))
        difficulty = "{:,}".format(gettopblock['block_header']['difficulty'])
        hashrate = str(hhashes(int(gettopblock['block_header']['difficulty']) / int(config.coin.DiffTarget)))
        height = "{:,}".format(gettopblock['block_header']['height'])
        reward = "{:,}".format(int(gettopblock['block_header']['reward'])/int(config.coin.decimal))
        if walletStatus is None:
            await ctx.send('**[ DEROGOLD ]**\n'
                            f'```[NETWORK HEIGHT] {height}\n'
                            f'[TIME]           {ago}\n'
                            f'[DIFFICULTY]     {difficulty}\n'
                            f'[BLOCK REWARD]   {reward}{COIN_REPR}\n'
                            f'[NETWORK HASH]   {hashrate}\n```')
            return
        else:
            localDaemonBlockCount = int(walletStatus['blockCount'])
            networkBlockCount = int(walletStatus['knownBlockCount'])
            t_percent = '{:,.2f}'.format(truncate(localDaemonBlockCount/networkBlockCount*100,2))
            t_localDaemonBlockCount = '{:,}'.format(localDaemonBlockCount)
            t_networkBlockCount = '{:,}'.format(networkBlockCount)
            await ctx.send('**[ DEROGOLD ]**\n'
                            f'```[NETWORK HEIGHT] {height}\n'
                            f'[TIME]           {ago}\n'
                            f'[DIFFICULTY]     {difficulty}\n'
                            f'[BLOCK REWARD]   {reward}{COIN_REPR}\n'
                            f'[NETWORK HASH]   {hashrate}\n'
                            f'[WALLET SYNC %]: {t_percent}\n```'
                            )
            return
    else:
        await ctx.send('`Unavailable.`')
        return


@bot.command(pass_context=True, help=bot_help_tag)
async def tag(ctx, *args):
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f'{EMOJI_STOPSIGN} This command can not be in private.')
        return

    if len(args) == 0:
        ListTag = store.sql_tag_by_server(str(ctx.message.guild.id))
        if len(ListTag) > 0:
            tags = (', '.join([w['tag_id'] for w in ListTag])).lower()
            await ctx.send(f'Available tag: `{tags}`.\nPlease use `.tag tagname` to show it in detail.'
                          'If you have permission to manage discord server.\n'
                          'Use: `.tag -add|del tagname <Tag description ... >`')
            return
        else:
            await ctx.send('There is no tag in this server. Please add.\n'
                            'If you have permission to manage discord server.\n'
                            'Use: `.tag -add|-del tagname <Tag description ... >`')
            return
    elif len(args) == 1:
        TagIt = store.sql_tag_by_server(str(ctx.message.guild.id), args[0].upper())
        if TagIt:
            tagDesc = TagIt['tag_desc']
            await ctx.send(f'{tagDesc}')
            return
        else:
            await ctx.send(f'There is no tag {args[0]} in this server.\n'
                            'If you have permission to manage discord server.\n'
                            'Use: `.tag -add|-del tagname <Tag description ... >`')
            return
    if (args[0].lower() in ['-add', '-del']) and ctx.author.guild_permissions.manage_guild == False:
        await ctx.send('Permission denied.')
        return
    if args[0].lower() == '-add' and ctx.author.guild_permissions.manage_guild:
        if (re.match('^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$', args[1])):
            tag=args[1].upper()
            if (len(tag)>=32):
                await ctx.send(f'Tag ***{args[1]}*** is too long.')
                return
            
            tagDesc = ctx.message.content.strip()[(9+len(tag)+1):]
            if (len(tagDesc)<=3):
                await ctx.send(f'Tag desc for ***{args[1]}*** is too short.')
                return
            addTag = store.sql_tag_by_server_add(str(ctx.message.guild.id), tag.strip(), tagDesc.strip(), ctx.message.author.name, str(ctx.message.author.id))
            if (addTag is None):
                await ctx.send(f'Failed to add tag ***{args[1]}***')
                return
            if (addTag.upper()==tag.upper()):
                await ctx.send(f'Successfully added tag ***{args[1]}***')
                return
            else:
                await ctx.send(f'Failed to add tag ***{args[1]}***')
                return
        else:
            await ctx.send(f'Tag {args[1]} is not valid.')
            return
        return
    elif args[0].lower() == '-del' and ctx.author.guild_permissions.manage_guild:
        if (re.match('^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$', args[1])):
            tag=args[1].upper()
            delTag = store.sql_tag_by_server_del(str(ctx.message.guild.id), tag.strip())
            if (delTag is None):
                await ctx.send(f'Failed to delete tag ***{args[1]}***')
                return
            if (delTag.upper()==tag.upper()):
                await ctx.send(f'Successfully deleted tag ***{args[1]}***')
                return
            else:
                await ctx.send(f'Failed to delete tag ***{args[1]}***')
                return
        else:
            await ctx.send(f'Tag {args[1]} is not valid.')
            return
        return


def hhashes(num) -> str:
    for x in ['H/s','KH/s','MH/s','GH/s']:
        if num < 1000.0:
            return "%3.1f%s" % (num, x)
        num /= 1000.0
    return "%3.1f%s" % (num, 'TH/s')


@register.error
async def register_error(error, ctx):
    pass


@info.error
async def info_error(error, ctx):
    pass


@balance.error
async def balance_error(error, ctx):
    pass


@botbalance.error
async def botbalance_error(error, ctx):
    pass


@withdraw.error
async def withdraw_error(error, ctx):
    pass


@tip.error
async def tip_error(error, ctx):
    pass


@tipall.error
async def tipall_error(error, ctx):
    pass


@send.error
async def send_error(error, ctx):
    pass


@address.error
async def address_error(error, ctx):
    pass


@paymentid.error
async def payment_error(error, ctx):
    pass


@tag.error
async def tag_error(error, ctx):
    pass


@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.message.author.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.message.author.send('Sorry. This command is disabled and cannot be used.')
    elif isinstance(error, commands.MissingRequiredArgument):
        command = _.message.content.split()[0].strip('.')
        await ctx.message.author.send('Missing an argument: try `.help` or `.help ' + command + '`')
    elif isinstance(error, commands.CommandNotFound):
        pass
        #await ctx.message.author.send('I don\'t know that command: try `.help`')


# Multiple tip
async def _tip(ctx, amount):
    # Check if maintenance
    if IS_MAINTENANCE == 1:
        if int(ctx.message.author.id) in MAINTENANCE_OWNER:
            pass
        else:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} {config.maintenance_msg}')
            return
    else:
        pass
    # End Check if maintenance

    user_from = store.sql_get_userwallet(str(ctx.message.author.id))
    notifyList = store.sql_get_tipnotify()

    try:
        amount = float(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid amount.')
        return

    try:
        real_amount = int(round(float(amount) * COIN_DIGITS))
    except:
        await ctx.send(f"{EMOJI_STOPSIGN} {ctx.author.mention} Amount must be a number.")
        return

    if real_amount > config.max_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be bigger than '
                        f'{config.max_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    listMembers = ctx.message.mentions

    memids = []  ## list of member ID
    for member in listMembers:
        if ctx.message.author.id != member.id:
            if member.bot == False:
                memids.append(str(member.id))

    ActualSpend = real_amount * len(memids)
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))
    if ActualSpend >= user_from['actual_balance'] + int(userdata_balance['Adjust']):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Insufficient balance to send total tip of '
                        f'{ActualSpend / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    if ActualSpend > config.max_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Total Transaction cannot be bigger than '
                        f'{config.max_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Total Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    tips = None
    try:
        # sql_mv_tx_multiple(user_from: str, user_name: str, user_tos, server_id: str, servername: str, messageid: str, amount_each: int, tiptype: str)
        tips = store.sql_mv_tx_multiple(str(ctx.message.author.id), str(ctx.message.author.name), memids, str(ctx.guild.id), str(ctx.guild.name), str(ctx.message.id), int(real_amount), "TIPS")
    except Exception as e:
        print(e)
    if tips:
        await ctx.message.add_reaction(EMOJI_MONEYBAG)
        if str(ctx.message.author.id) not in notifyList:
            try:
                await ctx.message.author.send(
                                        f'{EMOJI_MONEYBAG} Total tip of {ActualSpend / COIN_DIGITS:,.2f} '
                                        f'{COIN_REPR} '
                                        f'was sent to ({len(memids)}) members '
                                        f'in server: `{ctx.guild.name}`\n'
                                        f'Each: `{real_amount / COIN_DIGITS:,.2f}{COIN_REPR}`'
                                        f'Total spending: `{ActualSpend / COIN_DIGITS:,.2f}{COIN_REPR}`')
            except Exception as e:
                print('Adding: ' + str(ctx.message.author.id) + ' not to receive DM tip')
                store.sql_toggle_tipnotify(str(ctx.message.author.id), "OFF")
                print(e)
        for member in ctx.message.mentions:
            if ctx.message.author.id != member.id:
                if member.bot == False:
                    if str(member.id) not in notifyList:
                        try:
                            await member.send(
                                        f'{EMOJI_MONEYBAG} You got a tip of {real_amount / COIN_DIGITS:,.2f} '
                                        f'{COIN_REPR} from `{ctx.message.author.name}` '
                                        f'in server: `{ctx.guild.name}`\n'
                                        f'{NOTIFICATION_OFF_CMD}')
                        except Exception as e:
                            print('Adding: ' + str(member.id) + ' not to receive DM tip')
                            store.sql_toggle_tipnotify(str(member.id), "OFF")
                            print(e)
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Can not deliver TX right now. Try again soon.')
        return


# Multiple tip
async def _tip_talker(ctx, amount, list_talker):
    user_from = store.sql_get_userwallet(str(ctx.message.author.id))
    notifyList = store.sql_get_tipnotify()

    try:
        amount = float(amount)
    except ValueError:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Invalid amount.')
        return

    try:
        real_amount = int(round(float(amount) * COIN_DIGITS))
    except:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f"{ctx.author.mention} Amount must be a number.")
        return

    if real_amount > config.max_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be bigger than '
                        f'{config.max_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    memids = []  ## list of member ID
    for member_id in list_talker:
        if ctx.message.author.id != int(member_id):
            memids.append(str(member_id))

    ActualSpend = real_amount * len(memids)
    userdata_balance = store.sql_adjust_balance(str(ctx.message.author.id))

    if ActualSpend >= user_from['actual_balance'] + int(userdata_balance['Adjust']):
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Insufficient balance to send total tip of '
                        f'{ActualSpend / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    if ActualSpend > config.max_mv_amount:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Total Transaction cannot be bigger than '
                        f'{config.max_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return
    elif real_amount < config.min_mv_amount:
        #print('ActualSpend: '+str(ActualSpend))
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(
                        f'{EMOJI_STOPSIGN} {ctx.author.mention} Total Transaction cannot be smaller than '
                        f'{config.min_mv_amount / COIN_DIGITS:,.2f} '
                        f'{COIN_REPR}.')
        return

    tips = None
    try:
        # sql_mv_tx_multiple(user_from: str, user_name: str, user_tos, server_id: str, servername: str, messageid: str, amount_each: int, tiptype: str)
        tips = store.sql_mv_tx_multiple(str(ctx.message.author.id), str(ctx.message.author.name), memids, str(ctx.guild.id), str(ctx.guild.name), str(ctx.message.id), int(real_amount), "TIPS")
    except Exception as e:
        print(e)
    if tips:
        await ctx.message.add_reaction(EMOJI_MONEYBAG)
        await ctx.message.add_reaction(EMOJI_SPEAK)
        if str(ctx.message.author.id) not in notifyList:
            try:
                await ctx.message.author.send(
                                        f'{EMOJI_MONEYBAG} Total tip of {ActualSpend / COIN_DIGITS:,.2f} '
                                        f'{COIN_REPR} '
                                        f'was sent to ({len(memids)}) members for active talking '
                                        f'in server: `{ctx.guild.name}` channel: `{ctx.channel.name}`\n'
                                        f'Each: `{real_amount / COIN_DIGITS:,.2f}{COIN_REPR}`'
                                        f'Total spending: `{ActualSpend / COIN_DIGITS:,.2f}{COIN_REPR}`')
            except Exception as e:
                print('Adding: ' + str(ctx.message.author.id) + ' not to receive DM tip')
                store.sql_toggle_tipnotify(str(ctx.message.author.id), "OFF")
                print(e)
        mention_list_name = ''
        for member_id in list_talker:
            if ctx.message.author.id != int(member_id):
                member = bot.get_user(id=int(member_id))
                if member.bot == False:
                    mention_list_name = mention_list_name + '`'+member.name + '` '
                    if str(member_id) not in notifyList:
                        try:
                            await member.send(
                                        f'{EMOJI_MONEYBAG} You got a tip of {real_amount / COIN_DIGITS:,.2f} '
                                        f'{COIN_REPR} from `{ctx.message.author.name}` for active talking '
                                        f'in server : `{ctx.guild.name}` channel: `{ctx.channel.name}`\n'
                                        f'{NOTIFICATION_OFF_CMD}')
                        except Exception as e:
                            print('Adding: ' + str(member.id) + ' not to receive DM tip')
                            store.sql_toggle_tipnotify(str(member.id), "OFF")
                            print(e)
        await ctx.send(f'{mention_list_name}\n\nYou got tip :) for active talking in `{ctx.guild.name}` {ctx.channel.mention}:)')
        return
    else:
        await ctx.message.add_reaction(EMOJI_ERROR)
        await ctx.send(f'{EMOJI_STOPSIGN} {ctx.author.mention} Can not deliver Tip right now. Try again soon.')
        return


def truncate(number, digits) -> float:
    stepper = pow(10.0, digits)
    return math.trunc(stepper * number) / stepper


@click.command()
def main():
    bot.run(config.discord.token, reconnect=True)


if __name__ == '__main__':
    main()
