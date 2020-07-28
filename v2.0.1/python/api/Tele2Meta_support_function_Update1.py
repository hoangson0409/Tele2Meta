import numpy as np
from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector
import threading
import configparser
import json
import asyncio
from datetime import date, datetime
'''
All supporting function for Tele2Meta - Modifiable for  each channel
'''

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

    dwx = DWX_ZeroMQ_Connector()

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
#############################################################################################################
########### END OF MODIFIABLE PART DEPENDING ON EACH CHANNEL ################################################
#############################################################################################################