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
import smtplib   
import concurrent.futures
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode
from django.core.serializers.json import DjangoJSONEncoder
import datetime
import concurrent.futures
'''
All supporting function for Tele2Meta - Modifiable for  each channel
'''
global dwx
dwx = DWX_ZeroMQ_Connector()



#FUNCTION TO REMOVE EMOJI FROM TEXT
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
pending_wordlist = ['PENDING','Pending','pending','LIMIT','STOP','Limit','Stop','limit','stop']
def order_type_encoder(text):
    text = deEmojify(text)
    for i in pending_wordlist:
        if i in text:
            return -49
            break
        else:
            continue
        
    if ("BUY" in text.split()[:2]) or ("Buy" in text.split()[:2]) or ("buy" in text.split()[:2]) :
        return 0
    elif ("SELL" in text.split()[:2]) or ("Sell" in text.split()[:2]) or ("sell" in text.split()[:2]) :
        return 1

#FUNCTION TO IDENTIFY TRADE SYMBOL
symbol_list = ["EURUSD","EURCHF","EURAUD","EURCAD","EURNZD","EURJPY","EURGBP",
   "NZDCAD","NZDCHF","NZDUSD","NZDJPY",
   "USDJPY","USDCAD","USDCHF",
   "AUDUSD","AUDCAD","AUDCHF","AUDJPY","AUDNZD",
   "CADCHF","CADJPY","CHFJPY","CHFTRY",
   "GBPUSD","GBPJPY","GBPCAD","GBPCHF","GBPAUD","GBPNZD","XAUUSD","US30","USOIL","XTIUSD","GOLD",'USTEC']

def symbol_identifier(text):
    for i in symbol_list:
        if i in text:
            if i == 'GOLD':
                return 'XAUUSD'
                break
            elif i == 'XTIUSD':
                return 'USOIL'
                break
            else:
                return i.upper()
                break
        else:
            continue    
    return 'unidentified'

#FUNCTION TO CONVERT PRICE TO POINTS    
def priceToPoints(entry,another,symbol):
    if ('JPY' in symbol) or (symbol == 'XAUUSD') or (symbol == 'USOIL'):
        point_value = 0.001
    elif symbol == 'US30':
        point_value = 0.1
    elif symbol == 'USTEC':
        point_value = 0.01
    else:
        point_value = 0.00001
    return np.int(np.abs(another-entry) / point_value)

 
#############################################################################
#MOST IMPORTANT FUNCTION - CONVERT A TEXT INTO TRADE DICTIONARY##############
#############################################################################
numeric_wordlist = ['ENTRY','Entry','SL','Sl','TP','Tp','TP1', 'TP2','TP3','tp','sl']
tp_wordlist = ['TP', 'TP1', 'TP2', 'TP3','TP','Tp','tp']

def text_to_tradedict_2(text):

##################################################################  
#preprocessing for text - remove @, remove ':' by space and demojify
    text = deEmojify(text)
    
    if '@' in text:
        text = text.replace('@','')
    if ':' in text:
        text = text.replace(':',' ')

##################################################################
######INITIIALIZE IMPORTANT LIST##################################

    numeric_dict_list = [] #a dict of entry price, sl, tp price
    tp_dict_list = [] #a dict containing take profit info
    is_digit_list = [] #is_digit_list will return a true/false vector
##################################################################    
    #loop thru each word in message
    #store the word in numeric wordlist and the nextword (highly likely a number) as a dict, then put them in the numeric_dict_list
    #store all the nextword in a list, then check if isdigit(), then store in logical vector - is_digit_list
    for idx,cont in enumerate(text.split()):
        if cont in numeric_wordlist:
            nextword = text.split()[idx+1] 
            numeric_dict_list.append({cont:nextword}) 
            
            next_word_isnumeric = nextword.replace('.','',1).isdigit()
            is_digit_list.append(next_word_isnumeric)
    
    
    for i in numeric_dict_list: 
        if ('TP' in str(i.keys())) or ('Tp' in str(i.keys())) or ('tp' in str(i.keys())) :
            tp_dict_list.append(i) 
            
            
    print(numeric_dict_list)
    print(tp_dict_list)     
    print(is_digit_list)
#####################################################################
#if all nextword is digit - then proceed with trading 
#length of tp_dict_list is the number of trade
    
    if all(is_digit_list): 
        
        final_trade_dict_list = [] #a list that contains all trade dictionary to be sent
        number_of_trade = len(tp_dict_list)
        
        for idx1 in numeric_dict_list:
                if ('ENTRY' in str(idx1.keys())) or ('Entry' in str(idx1.keys())):
                    entry = np.float(list(idx1.values())[0])

        for idx2 in numeric_dict_list:
                if ('SL' in str(idx2.keys())) or ('Sl' in str(idx2.keys())) or ('sl' in str(idx2.keys())):
                    SL = np.float(list(idx2.values())[0])

        
        symbol = symbol_identifier(text)

        for i in range(number_of_trade):
            TP = np.float(list(tp_dict_list[i].values())[0])

            my_trade = {}
            my_trade['_action'] = 'OPEN'  
            my_trade['_type'] = order_type_encoder(text)
            my_trade['_symbol'] = symbol
            my_trade['_price'] = 0.0
            my_trade['_SL'] = priceToPoints(entry,SL,symbol)
            my_trade['_TP'] = priceToPoints(entry,TP,symbol)
            my_trade['_lots'] = 0.01
            my_trade['_magic']= 123456
            my_trade['_ticket']= 0
            
            final_trade_dict_list.append(my_trade)
        return final_trade_dict_list
    
    else:
        return None

########################################################################################################################
#FUNCTION TO SEND TRADE#################################################################################################
def trade_sender(_exec_dict):
    
    _lock = threading.Lock()

    _lock.acquire()

    response = dwx._DWX_MTX_NEW_TRADE_(_order=_exec_dict)

    _lock.release()

######################################################################################
#FUNCTION TO CHECK IF A MESSAGE IS TRADE SIGNAL AND REPEATED
#CONDITION TO BE A TRADE SIGNAL: MUST HAVE ENTRY or Entry // BUY OR SELL
#MUST HAVE NUMBER 
#MUST BE A MESSAGE


def hasNumbers(inputString):
    return any(char.isdigit() for char in inputString)

def is_tradesignal(all_messages,latest_message_id):
    if  (
        "message" in all_messages[0].keys() and  #Must be a message
        ('ENTRY' in all_messages[0]['message'] or 'Entry' in all_messages[0]['message']) and #MUST HAVE ENTRY or Entry
        ('BUY' in all_messages[0]['message'] or 'SELL' in all_messages[0]['message'] or
        'Buy' in all_messages[0]['message'] or 'Sell' in all_messages[0]['message'] or
        'buy' in all_messages[0]['message'] or 'sell' in all_messages[0]['message'] ) and  #Must contain the word buy or sell 
        hasNumbers(all_messages[0]['message']) and #Must have number within
        all_messages[0]['id'] != latest_message_id #Must have different ID from the last message
        ):
        return True
    else:
        return False 

def is_new_message(all_messages,latest_message_id):
    if  (
        "message" in all_messages[0].keys() and  #Must be a message
        all_messages[0]['id'] != latest_message_id #Must have different ID from the last message
        ):
        return True
    else:
        return False

def email_sender(email_to_send):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    try:
        s.starttls()
        s.login("hoangson0409@gmail.com", "methambeo1997") 
        s.sendmail("hoangson0409@gmail.com", "hoangson.comm.uavsnsw@gmail.com", email_to_send)
    except Exception as err:
        print("Error while sending email: ",err)
    finally:
        s.quit()

def find_tradeID():
    
    # _lock = threading.Lock()
    # _lock.acquire()
    resp = dwx._get_response_()
    # _lock.release()
    # XU LY response o day, return trade id
    if resp is not None:
        if '_ticket' in resp:
            return resp['_ticket']
    


def db_insert(latest_mess_id,trade_id_dict):
    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='tele3meta',
                                             user='shawn',
                                             password='password')
        

        cursor = connection.cursor()
        for i in trade_id_dict:
            mySql_insert_query = """INSERT INTO mess2trade (trade_id,message_id) VALUES ({tid},{mid}) """.format(tid=i,mid=latest_mess_id)
            cursor.execute(mySql_insert_query)
            connection.commit()

        print("Records inserted successfully into table mess2trade")
        cursor.close()

    except Error as error:
        print("Failed to insert record into table mess2trade. Error {}".format(error))

    finally:
        if (connection.is_connected()):
            connection.close()
            print("MySQL connection for mess2trade db_insert is closed")

def db_insert2(latest_mess_id,all_message): #for table message
    
    date_received = int(all_message['date'].timestamp())
    content = deEmojify(all_message['message'])
    raw_message = json.dumps(all_message,sort_keys=True,indent=1,cls=DjangoJSONEncoder)
    
    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='tele3meta',
                                             user='shawn',
                                             password='password')
        

        cursor = connection.cursor()
        
        mySql_insert_query2 = """INSERT INTO messages (message_id,date_received,content,raw_message) VALUES ({a},{b},'{c}','{d}') """.format(a=latest_mess_id,b=date_received,c=content,d=raw_message)
        cursor.execute(mySql_insert_query2)
        connection.commit()
        print("Records inserted succcessfully into table messages")
        
        cursor.close()

    except Error as error:
        print("Failed to insert record into table messages. Error {}".format(error))

    finally:
        if (connection.is_connected()):
            connection.close()
            print("MySQL connection for table messages is closed")



def trade_sender_and_findID(_exec_dict):
    _lock = threading.Lock()
    _lock.acquire()

    t = threading.Thread(name="Trader",target=trade_sender,args = (_exec_dict,))
    t.daemon = True
    t.start()
    t.join()

    time.sleep(2)
    resp = dwx._get_response_()
    _lock.release()

    if resp is not None:
        #Chi khi gui trade thanh cong - moi gui ve 
        if '_ticket' in resp and '_response' not in resp:
            resp['symbol'] = _exec_dict["_symbol"]
            resp["sl_in_points"] =  _exec_dict["_SL"]
            resp["tp_in_points"] =  _exec_dict["_TP"]

            return (resp['_ticket'],resp)

def read_and_write_disk(message):
    with open('channel_messages_phu.json','r') as json_file: 
        data = json.load(json_file)
        data.append(message)
    with open('channel_messages_phu.json', 'w') as outfile:
        json.dump(data, outfile, cls=DateTimeEncoder)


def is_new_hour(latest_hour):
    now = datetime.datetime.now()
    if  (
        now.hour != latest_hour
        ):
        return True
    else:
        return False

def get_open_trade_result():
    _lock = threading.Lock()
    _lock.acquire()
    dwx._DWX_MTX_GET_ALL_OPEN_TRADES_()
    _lock.release()
    

def get_open_trade_result_and_insertdb():
    _lock = threading.Lock()
    _lock.acquire()

    t = threading.Thread(name="get_open_trade_result",target=get_open_trade_result)
    t.daemon = True
    t.start()
    t.join()

    time.sleep(0.5)
    return_value = dwx._get_response_()
    _lock.release()

    print("this is return_value value from get_open_trade: ", return_value,"no more")

    if return_value is not None:
        
        try:
            connection = mysql.connector.connect(host='localhost',
                                             database='tele3meta',
                                             user='shawn',
                                             password='password')
            cursor = connection.cursor()
            
            for i in return_value["_trades"]:
                trade_id = i
                t_time = int(datetime.datetime.now().timestamp())
                pnl = return_value["_trades"][i]["_pnl"]
                mySql_insert_query = """INSERT INTO trade_info_pnl (trade_id,t_time,pnl) VALUES ({a},{b},{c}) """.format(a=trade_id,b=t_time,c=pnl)
                cursor.execute(mySql_insert_query)
                connection.commit()
            print("Records inserted successfully into table trade_info_pnl")
            cursor.close()
            
        except Error as error:
            print("Failed to insert record into table trade_info_pnl. Error {}".format(error))

        finally:
            if (connection.is_connected()):
                connection.close()
                print("MySQL connection for get_open_trade_result_and_insertdb is closed")




def new_db_insert(latest_mess_id,trade_id_dict,response_dict_list):
    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='tele3meta',
                                             user='shawn',
                                             password='password')
        

        cursor = connection.cursor()
        for i in trade_id_dict:
            mySql_insert_query = """INSERT INTO mess2trade (trade_id,message_id) VALUES ({tid},{mid}) """.format(tid=i,mid=latest_mess_id)
            cursor.execute(mySql_insert_query)
            connection.commit()
        
        
        
        print("Records inserted successfully into table mess2trade")
        for i in response_dict_list:
            trade_id = i["_ticket"]
            symbol = i["symbol"]
            open_time_str = i['_open_time']
            open_time = datetime.datetime.strptime(open_time_str, '%Y.%m.%d %H:%M:%S')
            open_time_unix = int(open_time.timestamp())
            open_price = i['_open_price']
            SL = i["_sl"]
            TP = i["_tp"]
            SL_in_points = i["sl_in_points"]
            TP_in_points = i['tp_in_points']
            mySql_insert_query = """INSERT INTO trade_info_static (trade_id,symbol,open_time,open_price,sl,tp,sl_in_points,tp_in_points) VALUES ({a},{b},{c},{e},{f},{g},{h}) """.format(a=trade_id,b=symbol,c=open_time_unix,d=open_price,e=SL,f=TP,g=SL_in_points,h=TP_in_points)
            cursor.execute(mySql_insert_query)
            connection.commit()
        
        print("Records inserted successfully into table trade_info_static")
        cursor.close()

    except Error as error:
        print("Failed to insert record into table mess2trade and trade_info_static. Error {}".format(error))

    finally:
        if (connection.is_connected()):
            connection.close()
            print("MySQL connection for db_insert is closed")

def send_trades_and_insertDB(trades_dict,latest_message_id):

    trade_id_dict = []
    trade_sender_response = []

    for i in range(len(trades_dict)):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(trade_sender_and_findID,trades_dict[i])
            trade_sender_result = future.result()

            if trade_sender_result is not None:
                trade_id = trade_sender_result[0]
                response = trade_sender_result[1]
                trade_id_dict.append(trade_id)
                trade_sender_response.append(response)

    print("Here is the trade_id_dict: ", trade_id_dict)
    
    if len(trade_id_dict) > 0:
        t = threading.Thread(name="dbInsert",target=new_db_insert,args = (latest_message_id,trade_id_dict,trade_sender_response,))
        t.daemon = True
        t.start()
        t.join()

#############################################################################################################
########### END OF MODIFIABLE PART DEPENDING ON EACH CHANNEL ################################################
#############################################################################################################