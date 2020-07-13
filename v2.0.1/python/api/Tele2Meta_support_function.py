import numpy as np
from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector
import threading
import configparser
import json
import asyncio
from datetime import date, datetime
#############################################################################################################
###########  MODIFIABLE PART DEPENDING ON EACH CHANNEL ######################################################
#############################################################################################################
#ALL SUPPORTING FUNCTION

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