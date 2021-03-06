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
from Tele2Meta_support_function_Update3 import ( 
    deEmojify, priceToPoints,text2TradeDict, isTradeSignal,
    hasNumbers,isNewMessage,DateTimeEncoder, emailSender, getRecentTradesAndSendEmail,
    getMessageAndInsertDB,getOpenTradesAndInsertDB,isNewHour,sendTradesAndInsertDB)
import smtplib   
import concurrent.futures
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode

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
shawn_pw = config['Telegram']['shawn_pw']

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



    ############################################################################################
    #Conditions to filter only trade signal
    #and a check part of last message
    
    ############################################################################
    #IN RA TIN NHAN CUOI CUNG
    if "message" in all_messages[0].keys():
        print('Here is the latest message: ', all_messages[0]['message']) 
        print('#########################################################')
    else:
        print('Here is the something latest not message: ', all_messages[0])
        print('#########################################################')
    #############################################################################
    #NEU LA TIN NHAN MOI, LA TRADE SIGNAL: IN THEM VAO CHANNEL MESSAGE, LAY ID
    #NEU LA TIN NHAN MOI, KHONG PHAI TRADE SIGNAL: LAY ID
    #NEU KHONG PHAI TIN NHAN MOI: LAY ID
    if isNewMessage(all_messages,latest_message_id): 
        #read_and_write_disk(all_messages[0]['message'])

        if  isTradeSignal(all_messages,latest_message_id):
            latest_message_text = all_messages[0]['message']
            trade_dict_list = text2TradeDict(latest_message_text)
            latest_message_id = all_messages[0]['id']
            return (trade_dict_list,latest_message_id,latest_message_text,all_messages[0])

        else:
            latest_message_text = all_messages[0]['message']
            latest_message_id = all_messages[0]['id']
            return (None,latest_message_id,latest_message_text,all_messages[0])

    else:
        latest_message_id = all_messages[0]['id']
        return (None,latest_message_id,None,all_messages[0])

    
   


####################################################################################
########MAIN PROGRAM BE RUNNING HERE################################################
####################################################################################
global latest_message_id 
latest_message_id = 0

global latest_hour
latest_hour = 25

dbconfig = {
  "host": "localhost",
  "user":     "shawn",
  "database":"tele3meta",
  "password":"password"
}
import mysql.connector.pooling
cnxpool = mysql.connector.pooling.MySQLConnectionPool(pool_name = "mypool",
                                                      pool_size = 5,
                                                      **dbconfig)

while True:
    
    with client:
        
        result = client.loop.run_until_complete(execute(phone,latest_message_id))
        latest_message_id = result[1]
        thread_list = []

        #at the beginning of new hour
        #get_open_trade_result_and_insertdb inserts into trade_pnl_info table
        if isNewHour(latest_hour):
            t4 = threading.Thread(name="getOpenTradesAndInsertDB",target=getOpenTradesAndInsertDB,args = (cnxpool,))
            t4.daemon = True
            t4.start()
            thread_list.append(t4)

        #db_insert2 inserts into table messages 
        if result[2] is not None: #if new message is found
            t3 = threading.Thread(name="getMessageAndInsertDB",target=getMessageAndInsertDB,args = (latest_message_id,result[3],cnxpool,))
            t3.daemon = True
            t3.start()
            thread_list.append(t3)

        if result[0] is not None: #if trade signal found in new message
            
            trades_dict = result[0]
            latest_message_text = result[2]

            # one thread to send email
            t1 = threading.Thread(name="getRecentTradesAndSendEmail",target=getRecentTradesAndSendEmail,args = (deEmojify(latest_message_text),cnxpool,))
            t1.daemon = True
            t1.start()
            thread_list.append(t1)

            #one thread to send trades and insert into tables: mess2trade and trade_info_static
            t2 = threading.Thread(name="sendTradesAndInsertDB",target=sendTradesAndInsertDB,args = (trades_dict,latest_message_id,cnxpool,))
            t2.daemon = True
            t2.start()
            thread_list.append(t2)

        latest_hour = datetime.now().hour
        for thr in thread_list:
                thr.join()

    
    time.sleep(30)

    continue


    
    


    
    
