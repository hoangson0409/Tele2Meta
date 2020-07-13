import os

#path2 = 'C:\\Users\\Admin\\Downloads\\dwx-zeromq-connector-master\\v2.0.1\\python\\api'
path2 = 'C:\\Users\\hoangson0409\\Downloads\\Tele2Meta\\v2.0.1\\python\\api'

os.chdir(path2)

from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector
import threading
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
from Tele2Meta_support_function import deEmojify, orderTypeEncode, priceToPoints,text_to_tradedict, trade_sender, is_tradesignal, DateTimeEncoder,is_new_message





# Reading Configs
#path3 = 'C:\\Users\\Admin\\Downloads\\dwx-zeromq-connector-master\\telegram-analysis-master'
path3 = 'C:\\Users\\hoangson0409\\Downloads\\Tele2Meta\\telegram-analysis-master'

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



async def execute(phone,latest_message_id,every_mess_since_on):
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

    
    #print(all_messages)

    #######################################################################
    #Conditions to filter only trade signal
    if "message" in all_messages[0].keys():
        print('Here is the latest message: ', all_messages[0]['message']) 
        print('#########################################################')
        

    else:
        print('Here is the something latest not message: ', all_messages[0])
        print('#########################################################')
    #############################################################################
    #NEU CO THEM TIN NHAN MOI : IN THEM VAO CHANNEL MESSAGE
    if is_new_message(all_messages,latest_message_id):    
        every_mess_since_on.append(all_messages[0]['message'])
        with open('channel_messages.json', 'w') as outfile:
            json.dump(every_mess_since_on, outfile, cls=DateTimeEncoder)

        if  is_tradesignal(all_messages,latest_message_id):

            latest_message_text = all_messages[0]['message']

            trade_dict_list = text_to_tradedict(latest_message_text)

            latest_message_id = all_messages[0]['id']

            return (trade_dict_list,latest_message_id)

        else:
            latest_message_id = all_messages[0]['id']
            return (None,latest_message_id)

    else:
        latest_message_id = all_messages[0]['id']
        return (None,latest_message_id)
        
    
   


####################################################################################
########MAIN PROGRAM BE RUNNING HERE################################################
####################################################################################
global latest_message_id 
latest_message_id = 0
global every_mess_since_on
every_mess_since_on = []

while True:
    with client:
        
        result = client.loop.run_until_complete(execute(phone,latest_message_id,every_mess_since_on))
        
        if result[0] is not None:

            three_trades_dict = result[0]
            
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

            time.sleep(30)

        else:
            latest_message_id = result[1]
            time.sleep(30)
            continue

    continue


    
    
