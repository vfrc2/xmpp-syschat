import xmpp, sys, logging, os, threading, time
import traceback
from chat import SysChat


logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

ch = None

secure_type_white = False
secure_users = [] #list of user what can run commands

keep_alive = True
keep_alive_interval = 5 #sec

receiveLoop = None
pipeLoop = None

isReadPipe = False
isReceiveMes = False

send_mes_pipe = './message.pipe'
send_user_list = [] #user to send message from mes pipe

def main():
	global log
	global ch, keep_alive, keep_alive_interval
	global send_user_list
	
	print "Jabber Sys Chat"

	#loading config

	secure_black = False
	secure_users = #[xmpp.JID("vfrc2@vfrc2.paata.ru")] #enable whitelist
	
	send_user_list = [xmpp.JID("vfrc2@vfrc2.paata.ru"),]

	while True:
		try:
			setupChat()

			while ch.noError:
				time.sleep(keep_alive_interval)

			raise Exception(ch.error)

		except Exception as err:
			_logError("Error while work: {0}", err)
			cleanChat()

			if not keep_alive: #no keepalive when exit
				break
			log.debug("Keep-alive rertrie in %s sec", keep_alive_interval)
			time.sleep(keep_alive_interval)
			pass
		except KeyboardInterrupt:
			break;

	cleanChat()
	pass

def setupChat(args=None):

	global log
	global ch, receiveLoop, pipeLoop
	global isReadPipe, isReceiveMes

	isReadPipe = True
	isReceiveMes = True

	ch = SysChat()

	ch.server_url = "vfrc2.paata.ru"
	ch.user = xmpp.JID("f6server@vfrc2.paata.ru")
	ch.password = "1234"

	try:
		ch.connectAndAuth()
	except Exception as err:
		raise Exception("Connection error", err)

	log.debug("Start receive message loop")
	receiveLoop = threading.Thread(target=receiveMessageLoop)
	receiveLoop.daemon = True
	receiveLoop.start()

	log.debug("Start message pipe loop")
	pipeLoop = threading.Thread(target=fileMessagesLoop)
	pipeLoop.daemon = True
	pipeLoop.start()

	ch.startChat()

	pass


def cleanChat():
	global ch, receiveLoop, pipeLoop, log
	
	log.debug("Clean up session")

	try:
		
		if ch:
			ch.close()

		ch = None	

		if receiveLoop:
			isReceiveMes = False
			receiveLoo = None

		if pipeLoop:
			isReadPipe = False
			pipeLoop = None

	except Exception as err:
		_logError('Error while clean session {0}',err)
		pass

	pass

def receiveMessageLoop():

	global isReceiveMes, ch

	while isReceiveMes:
		try:
			mes = ch.getMessage(timeout=0.5)
			if mes:
				u_from = mes.getFrom()
				text = mes.getBody()
				log.debug("Echo message %s from %s", text, u_from)
				ch.pushMessage(text, user=u_from)
		except Exception as exp:
			_logError("Can't get message: {0}", exp)
		pass
	pass

def fileMessagesLoop():
	global log, ch, send_user_list
	global isReadPipe
	
	try:
		log.info("Start reading message")

		if len(send_user_list) == 0:
			log.info("No user for message pipe")

		if not os.path.exists(send_mes_pipe):
			log.debug("Create fifo pipe for messages")
			os.mkfifo(send_mes_pipe)

		while isReadPipe:
			log.debug("Waiting for message")
			line = file(send_mes_pipe, "r").read()
			if len(line) > 0:
				for us in send_user_list:
					mes = ch.createMessage(line, user=us)
					ch.pushMessage(mes)
			time.sleep(1)
	except Exception as err:
		_logError("Error create message pipe", err)

	pass

def _logError(text, exp):
	log.error(text.format(exp))
	log.debug(traceback.format_exc())

if __name__ == "__main__":
	main()