import os

path2 = 'C:\\Users\\Admin\\Downloads\\dwx-zeromq-connector-master\\v2.0.1\\python\\api'

os.chdir(path2)

from DWX_ZeroMQ_Connector_v2_0_1_RC8 import DWX_ZeroMQ_Connector
import threading



my_trade2 = {}
my_trade2['_action'] = 'OPEN'
my_trade2['_type'] = 0
my_trade2['_symbol'] = 'AUDUSD'
my_trade2['_price'] = 0.0
my_trade2['_SL'] = 0
my_trade2['_TP'] = 0
my_trade2['_lots'] = 0.01
my_trade2['_magic']= 123456
my_trade2['_ticket']= 0

my_trade3 = {}
my_trade3['_action'] = 'OPEN'
my_trade3['_type'] = 0
my_trade3['_symbol'] = 'EURJPY'
my_trade3['_price'] = 0.0
my_trade3['_SL'] = 0
my_trade3['_TP'] = 0
my_trade3['_lots'] = 0.01
my_trade3['_magic']= 123456
my_trade3['_ticket']= 0


def trade_sender(_exec_dict):
	_lock = threading.Lock()

	dwx = DWX_ZeroMQ_Connector()

	_lock.acquire()

	response = dwx._DWX_MTX_NEW_TRADE_(_order=_exec_dict)

	_lock.release()

	#return response



if __name__ == '__main__':
	print(my_trade3)
	trade2_sender = threading.Thread(target=trade_sender,args = (my_trade2,))
	trade3_sender = threading.Thread(target=trade_sender,args = (my_trade3,))
	trade2_sender.start()
	trade3_sender.start()
	trade2_sender.join()
	trade3_sender.join()




