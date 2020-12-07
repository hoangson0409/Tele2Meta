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
import pandas as pd
import time
import smtplib   
import concurrent.futures
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode
from django.core.serializers.json import DjangoJSONEncoder
import datetime
import concurrent.futures
from os.path import basename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import six
import os
import matplotlib.pyplot as plt
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
def orderTypeEncoder(text):
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

def symbolIdentifier(text):
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

def text2TradeDict(text):

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

        
        symbol = symbolIdentifier(text)

        for i in range(number_of_trade):
            TP = np.float(list(tp_dict_list[i].values())[0])

            my_trade = {}
            my_trade['_action'] = 'OPEN'  
            my_trade['_type'] = orderTypeEncoder(text)
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
def tradeSender(_exec_dict):
    
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

def isTradeSignal(all_messages,latest_message_id):
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

def isNewMessage(all_messages,latest_message_id):
    if  (
        "message" in all_messages[0].keys() and  #Must be a message
        all_messages[0]['id'] != latest_message_id #Must have different ID from the last message
        ):
        return True
    else:
        return False

def emailSender(email_to_send):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    try:
        s.starttls()
        s.login("hoangson0409@gmail.com", "methambeo1997") 
        s.sendmail("hoangson0409@gmail.com", "hoangson.comm.uavsnsw@gmail.com", email_to_send)
    except Exception as err:
        print("Error while sending email: ",err)
    finally:
        s.quit()



def getMessageAndInsertDB(latest_mess_id,all_message): #for table message
    
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
            print("MySQL connection for table getMessageAndInsertDB is closed")



# def read_and_write_disk(message):
#     with open('channel_messages_phu.json','r') as json_file: 
#         data = json.load(json_file)
#         data.append(message)
#     with open('channel_messages_phu.json', 'w') as outfile:
#         json.dump(data, outfile, cls=DateTimeEncoder)


def isNewHour(latest_hour):
    now = datetime.datetime.now()
    if  (
        now.hour != latest_hour
        ):
        return True
    else:
        return False

def getOpenTradesResult():
    _lock = threading.Lock()
    _lock.acquire()
    dwx._DWX_MTX_GET_ALL_OPEN_TRADES_()
    _lock.release()
    

def getOpenTradesAndInsertDB():
    _lock = threading.Lock()
    _lock.acquire()

    t = threading.Thread(name="getOpenTradesResult",target=getOpenTradesResult)
    t.daemon = True
    t.start()
    t.join()

    time.sleep(0.5)
    return_value = dwx._get_response_()
    _lock.release()

    print("this is return_value value from getOpenTradesAndInsertDB: ", return_value,"no more")

    if return_value is not None and "_trades" in return_value:
        
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
                print("MySQL connection for getOpenTradesAndInsertDB is closed")




def dbInsert_0(latest_mess_id,trade_id_dict,response_dict_list):
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
            mySql_insert_query = """INSERT INTO trade_info_static (trade_id,symbol,open_time,open_price,sl,tp,sl_in_points,tp_in_points) VALUES ({a},'{b}',{c},{d},{e},{f},{g},{h}) """.format(a=trade_id,b=symbol,c=open_time_unix,d=open_price,e=SL,f=TP,g=SL_in_points,h=TP_in_points)
            cursor.execute(mySql_insert_query)
            connection.commit()
        
        print("Records inserted successfully into table trade_info_static")
        cursor.close()

    except Error as error:
        print("Failed to insert record into table mess2trade and/or trade_info_static. Error {}".format(error))

    finally:
        if (connection.is_connected()):
            connection.close()
            print("MySQL connection for sendTradesAndInsertDB is closed")


def sendTradesAndFindID(_exec_dict):
    _lock = threading.Lock()
    _lock.acquire()

    t = threading.Thread(name="tradeSender",target=tradeSender,args = (_exec_dict,))
    t.daemon = True
    t.start()
    t.join()

    time.sleep(2)
    resp = dwx._get_response_()
    _lock.release()

    print('here is the resp value: ',resp)

    if resp is not None:
        #Chi khi gui trade thanh cong - moi gui ve 
        if '_ticket' in resp and '_response' not in resp:
            resp['symbol'] = _exec_dict["_symbol"]
            resp["sl_in_points"] =  _exec_dict["_SL"]
            resp["tp_in_points"] =  _exec_dict["_TP"]

            return (resp['_ticket'],resp)

def sendTradesAndInsertDB(trades_dict,latest_message_id):

    trade_id_dict = []
    trade_sender_response = []

    for i in range(len(trades_dict)):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(sendTradesAndFindID,trades_dict[i])
            trade_sender_result = future.result()

            if trade_sender_result is not None:
                trade_id = trade_sender_result[0]
                response = trade_sender_result[1]
                trade_id_dict.append(trade_id)
                trade_sender_response.append(response)

    print("Here is the trade_id_dict: ", trade_id_dict)
    
    if len(trade_id_dict) > 0:
        t = threading.Thread(name="dbInsert",target=dbInsert_0,args = (latest_message_id,trade_id_dict,trade_sender_response,))
        t.daemon = True
        t.start()
        t.join()



# def runQuery(query):
#     cnx = mysql.connector.connect(host = 'localhost', port = '3306', user='shawn', database='tele3meta',
#                      password='password')
#     cursor = cnx.cursor()
#     cursor.execute(query)
#     columns = cursor.description
#     result = []
#     for value in cursor.fetchall():
#         tmp = {}
#         for (index,column) in enumerate(value):
#             tmp[columns[index][0]] = column
#             result.append(tmp)
#     #data = cursor.fetchall()
#     data = pd.DataFrame(result).drop_duplicates(subset=None, keep='first', inplace=False)
#     cnx.disconnect
#     return data



# def renderTableAndGenImg(data, col_width=3.0, row_height=0.625, font_size=14,
#                      header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
#                      bbox=[0, 0, 1, 1], header_columns=0,
#                      ax=None, **kwargs):
#     if ax is None:
#         size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
#         fig, ax = plt.subplots(figsize=size)
#         ax.axis('off')

#     mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

#     mpl_table.auto_set_font_size(False)
#     mpl_table.set_fontsize(font_size)

#     for k, cell in  six.iteritems(mpl_table._cells):
#         cell.set_edgecolor(edge_color)
#         if k[0] == 0 or k[1] < header_columns:
#             cell.set_text_props(weight='bold', color='w')
#             cell.set_facecolor(header_color)
#         else:
#             cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
#     fig = ax.get_figure()
#     fig.savefig("output.png")
#     return None

# def sendEmailWithAttachment(subject, message, from_email, to_email=[], attachment=[]):
#     """
#     :param subject: email subject
#     :param message: Body content of the email (string), can be HTML/CSS or plain text
#     :param from_email: Email address from where the email is sent
#     :param to_email: List of email recipients, example: ["a@a.com", "b@b.com"]
#     :param attachment: List of attachments, exmaple: ["file1.txt", "file2.txt"]
#     """
#     msg = MIMEMultipart()
#     msg['Subject'] = subject
#     msg['From'] = from_email
#     msg['To'] = ", ".join(to_email)
#     msg.attach(MIMEText(message, 'html'))

#     for f in attachment:
#         with open(f, 'rb') as a_file:
#             basename = os.path.basename(f)
#             part = MIMEApplication(a_file.read(), Name=basename)

#         part['Content-Disposition'] = 'attachment; filename="%s"' % basename
#         msg.attach(part)

# #     email = smtplib.SMTP('your-smtp-host-name.com')
# #     email.sendmail(from_email, to_email, msg.as_string())
    
#     s = smtplib.SMTP('smtp.gmail.com', 587)
#     try:
#         s.starttls()
#         s.login("hoangson0409@gmail.com", "methambeo1997") 
#         s.sendmail(from_email, to_email, msg.as_string())
#     except Exception as err:
#         print("Error while sending email: ",err)
#     finally:
#         s.quit()



# def getRecentTradesAndSendEmail(message):
#     """
#     :param subject: email subject
#     :param message: Body content of the email (string), can be HTML/CSS or plain text
#     :param from_email: Email address from where the email is sent
#     :param to_email: List of email recipients, example: ["a@a.com", "b@b.com"]
#     :param attachment: List of attachments, exmaple: ["file1.txt", "file2.txt"]
#     """
    
    
#     query = '''select tis.trade_id, tis.symbol, sec_to_time(unix_timestamp(NOW()) - tis.open_time) as trade_opened_duration,  
# (tis.sl_in_points / 10) as slInPips, (tis.tp_in_points / 10) as tpInPips, tbr.best_profit
# from trade_info_static tis left join trade_best_results tbr on tis.trade_id = tbr.trade_id
# where tis.open_time  > unix_timestamp(now() - interval 48 hour);'''

#     print("this is data pulled from mysql: ",data)

#     with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
#             future = executor.submit(renderTableAndGenImg,data)
#             none = future.result()
   
#     sendEmailWithAttachment("Trade Info", message, "hoangson0409@gmail.com", ['hoangson.comm.uavsnsw@gmail.com'], attachment=['output.png'])
#############################################################################################################
########### END OF MODIFIABLE PART DEPENDING ON EACH CHANNEL ################################################
#############################################################################################################