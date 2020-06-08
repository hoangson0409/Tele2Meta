import os

path2 = 'C:\\Users\\Admin\\Downloads\\dwx-zeromq-connector-master\\v2.0.1\\python\\api'

os.chdir(path2)

from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector
import threading



from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector

import configparser
import json
import asyncio
from datetime import date, datetime

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import (GetHistoryRequest)
from telethon.tl.types import (
    PeerChannel
)
import numpy as np
import time



#############################################################################################################
###########  MODIFIABLE PART DEPENDING ON EACH CHANNEL ######################################################
#############################################################################################################
# some functions to parse json date
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, bytes):
            return list(o)

        return json.JSONEncoder.default(self, o)


def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')

#FUNCTION TO ENCODE BUY AND SELL
def orderTypeEncode(string):
    if string == 'BUY':
        return 0
    elif string == "SELL":
        return 1

#FUNCTION TO CONVERT PRICE TO POINTS
def priceToPoints(entry,another,symbol):
    if 'JPY' in symbol:
        point_value = 0.001
    else:
        point_value = 0.00001
    return np.int(np.abs(another-entry) / point_value)
 
def text_to_tradedict(text):

    symbol = text.split()[0]
    entry = float(deEmojify(text.split()[3]))
    SL = float(deEmojify(text.split()[5]))
    TP1 = float(deEmojify(text.split()[7]))
    TP2 = float(deEmojify(text.split()[9]))
    TP3 = float(deEmojify(text.split()[11]))

    my_trade1 = {}
    my_trade1['_action'] = 'OPEN'
    my_trade1['_type'] = orderTypeEncode(text.split()[1])
    my_trade1['_symbol'] = symbol
    my_trade1['_price'] = 0.0
    my_trade1['_SL'] = priceToPoints(entry,SL,symbol)
    my_trade1['_TP'] = priceToPoints(entry,TP1,symbol)
    my_trade1['_lots'] = 0.01
    my_trade1['_magic']= 123456
    my_trade1['_ticket']= 0

    my_trade2 = {}
    my_trade2['_action'] = 'OPEN'
    my_trade2['_type'] = orderTypeEncode(text.split()[1])
    my_trade2['_symbol'] = symbol
    my_trade2['_price'] = 0.0
    my_trade2['_SL'] = priceToPoints(entry,SL,symbol)
    my_trade2['_TP'] = priceToPoints(entry,TP2,symbol)
    my_trade2['_lots'] = 0.01
    my_trade2['_magic']= 123456
    my_trade2['_ticket']= 0

    my_trade3 = {}
    my_trade3['_action'] = 'OPEN'
    my_trade3['_type'] = orderTypeEncode(text.split()[1])
    my_trade3['_symbol'] = symbol
    my_trade3['_price'] = 0.0
    my_trade3['_SL'] = priceToPoints(entry,SL,symbol)
    my_trade3['_TP'] = priceToPoints(entry,TP3,symbol)
    my_trade3['_lots'] = 0.01
    my_trade3['_magic']= 123456
    my_trade3['_ticket']= 0

    return [my_trade1,my_trade2,my_trade3]

def trade_sender(_exec_dict):
    
    _lock = threading.Lock()

    dwx = DWX_ZeroMQ_Connector()

    _lock.acquire()

    response = dwx._DWX_MTX_NEW_TRADE_(_order=_exec_dict)

    _lock.release()

def is_tradesignal(all_messages,latest_message_id):
    if  (
        all_messages[0]['_'] == "Message"  and  #Must be a message
        5 <= len(all_messages[0]['message'].split()[0]) <= 6 and #First word of message must be 5 to 6 letters
        ('BUY' in all_messages[0]['message'] or 'SELL' in all_messages[0]['message']) and #Must contain the word buy or sell in message content
        all_messages[0]['id'] != latest_message_id #Must have different ID from the last message
        ):
        return True
    else:
        return False 
#############################################################################################################
########### END OF MODIFIABLE PART DEPENDING ON EACH CHANNEL ################################################
#############################################################################################################


# Reading Configs
path3 = 'C:\\Users\\Admin\\Downloads\\dwx-zeromq-connector-master\\telegram-analysis-master'

os.chdir(path3)
config = configparser.ConfigParser()
config.read("config.ini")

# Setting configuration values
api_id = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']

api_hash = str(api_hash)

phone = config['Telegram']['phone']
username = config['Telegram']['username']
channel = config['Telegram']['channel']

# Create the client and connect
client = TelegramClient(username, api_id, api_hash)



async def execute(phone,latest_message_id):
    await client.start()
    print("Client Created")
    # Ensure you're authorized
    if await client.is_user_authorized() == False:
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone, input('Enter the code: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Password: '))

    me = await client.get_me()

    user_input_channel = channel
    entity = user_input_channel
    # if user_input_channel.isdigit():
    #     entity = PeerChannel(int(user_input_channel))
    # else:
    #     entity = user_input_channel

    my_channel = await client.get_input_entity(entity)

    offset_id = 0
    limit = 1
    all_messages = []
    total_messages = 0
    total_count_limit = 1

    while True:
        print("Current Offset ID is:", offset_id, "; Total Messages:", total_messages)
        history = await client(GetHistoryRequest(
            peer=my_channel,
            offset_id=offset_id,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))
        if not history.messages:
            break
        messages = history.messages 
        for message in messages:
            all_messages.append(message.to_dict())
        offset_id = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break

    #with open('channel_messages.json', 'w') as outfile:
        #json.dump(all_messages, outfile, cls=DateTimeEncoder)
    #print(all_messages)

    #######################################################################
    #Conditions to filter only trade signal
    
    
    
     

    if  is_tradesignal(all_messages,latest_message_id):

        latest_message_text = all_messages[0]['message']

        trade_dict_list = text_to_tradedict(latest_message_text)

        latest_message_id = all_messages[0]['id'] 

        return (trade_dict_list,latest_message_id)

    else:
        return None

    
   




####################################################################################
global latest_message_id 
latest_message_id = 0

while True:
    with client:

        result = client.loop.run_until_complete(execute(phone,latest_message_id))

        if result is not None:
            three_trades_dict = result[0]
            
            # print(three_trades_dict)
            # print('#########################################')
            # print(three_trades_dict[0])
            trade1_sender = threading.Thread(target=trade_sender,args = (three_trades_dict[0],))
            trade2_sender = threading.Thread(target=trade_sender,args = (three_trades_dict[1],))
            trade3_sender = threading.Thread(target=trade_sender,args = (three_trades_dict[2],))

            trade1_sender.start()
            trade2_sender.start()
            trade3_sender.start()

            trade1_sender.join()
            trade2_sender.join()
            trade3_sender.join()
            latest_message_id = result[1]
        else:
            continue
          
        time.sleep(60)

    continue


    
    
