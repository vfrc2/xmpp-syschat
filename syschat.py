import xmpp, sys, logging, os, threading, time
import traceback
import argparse
import yaml
import execute

from chat import SysChat


logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

args = None

ch = None
exe = None

login = None
password = None
server = None

chroot = '/tmp'
secure_black = False
secure_users = [] #list of user what can run commands

keep_alive = True
keep_alive_interval = 5 #sec

receiveLoop = None
pipeLoop = None

isReadPipe = False
isReceiveMes = False

send_mes_pipe = None
send_user_list = [] #user to send message from mes pipe

def main():
	global log, args
	global ch, keep_alive, keep_alive_interval
	global send_user_list
	
	try:
		print "Jabber Sys Chat"

		args = parseArgs()

		loadConfig(args)

		loadArgs()

		checkConfig()

	except Exception as err:
		_logError("Error start: {0}", err)
		return


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
	global login, password

	isReadPipe = True
	isReceiveMes = True

	ch = SysChat()

	ch.user = login

	if not server:
		ch.server_url = login.getDomain()

	ch.password = password

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

def parseArgs():

	parser = argparse.ArgumentParser(\
		description='XMPP chatbot, what execute scripts and piped output to message')
	
	parser.add_argument('--pid', nargs=1, help="path to pid file")

	serv = parser.add_argument_group('server',\
		description="run client and wait for messages from pipe or from jabber")
	
	serv.add_argument('-c','--config', nargs='?',\
	 	help="config file yaml")
	serv.add_argument('-s','--xmpp-server', nargs=1,\
		help="ip or url of jabber server host[:port=5222]")
	serv.add_argument('-u','--user', nargs=1,\
		help="jid account for auth name@server")
	serv.add_argument('-p','--password', nargs=1,\
		help="password")
	serv.add_argument('--passfile', nargs=1,\
		help="file which store password")

	serv.add_argument('--pipe-file', nargs=1,\
		help="file path to create fifo pipe")
	serv.add_argument('--to-jid', nargs='*',\
		help="jid account(s) for send messages")

	serv.add_argument('--chroot', nargs=1,\
		help="chrootdir for commands def=\"~\"")
	serv.add_argument('--filter', nargs=1,\
		choices=['allow','deny'],\
		help="type of filter can be a(llow) or d(eny)")
	serv.add_argument('--users', nargs='*',\
		help="list of user allowed or denied to exec commands")
	serv.add_argument('--server', action='store_true',\
		help="run client and wait for messages from pipe or from jabber",\
		required= False)

	snd = parser.add_argument_group('send',\
		description="send message to message pipe from config")

	snd.add_argument('--send', nargs=1, \
		help="send MESSAGE", required= False)

	

	return parser.parse_args()

def loadConfig(args):

	global login
	global password
	global server

	global chroot
	global secure_black
	global secure_users

	global keep_alive 
	global keep_alive_interval

	global send_mes_pipe
	global send_user_list

	if not args.config:
		return

	if not os.path.exists(args.config):
		raise Exception("Can't find config file")

	cfg = yaml.load(open(args.config))

	cxmpp = cfg['xmpp']

	if not cxmpp:
		raise Exception("Wrong config need xmpp section")

	if 'login' in cxmpp.keys():
		login = xmpp.JID(cxmpp['login'])

	if 'password' in cxmpp.keys():
		password = cxmpp['password']

	if 'passfile' in cxmpp.keys():
		password = open(cxmpp['passfile'],'r').readline()

	if 'server' in cxmpp.keys():
		server = cxmpp['server']

	if 'keepalive' in cxmpp.keys():
		keep_alive = cxmpp['keepalive']

	if 'keepalive-interval' in cxmpp.keys():
		keep_alive_interval = cxmpp['keepalive-interval']


	cmessage_pipe = cfg['message_pipe']

	print cmessage_pipe

	if cmessage_pipe:
		if 'pipe-file' in cmessage_pipe.keys():
			send_mes_pipe = cmessage_pipe['pipe-file']

		send_user_list = []

		if 'to' in cmessage_pipe.keys():
			if type(cmessage_pipe['to']) == list:
				send_user_list = [xmpp.JID(x) for x in cmessage_pipe['to']]
			else:
				send_user_list = [xmpp.JID(str(cmessage_pipe['to']))]

	ccommand = cfg['cmd_exec']

	if ccommand:
		if 'chroot' in ccommand.keys():
			chroot = ccommand['chroot']

		if 'filter' in ccommand.keys() and \
				ccommand['chroot'] == 'deny':
			secure_black = True

		if 'users' in ccommand.keys():
			if type(ccommand['users']) == list:
				secure_users = [xmpp.JID(x) for x in ccommand['users']]
			else:
				secure_users = [xmpp.JID(str(ccommand['users']))]



def loadArgs():
	global args

	global login
	global password
	global server

	global chroot
	global secure_black
	global secure_users

	global keep_alive 
	global keep_alive_interval

	global send_mes_pipe
	global send_user_list

	if args.user:
		login = xmpp.JID(args.user)

	if args.password:
		password = args.password

	if args.passfile:
		password = open(args.passfile,'r').readline()

	if args.xmpp_server:
		server = args.xmpp_server

	# if 'keepalive' in cxmpp.keys():
	# 	keep_alive = cxmpp['keepalive']

	# if 'keepalive-interval' in cxmpp.keys():
	# 	keep_alive_interval = cxmpp['keepalive-interval']

	pass

def checkConfig():
	global login
	global password
	global server

	if not login or not password:
		raise Exception('User and password not configured') 




def receiveMessageLoop():

	global isReceiveMes, ch

	while isReceiveMes:
		try:
			mes = ch.getMessage(timeout=0.5)
			
			if mes and mes.getType() == 'chat' \
				and mes.getBody():

				u_from = mes.getFrom()
				text = mes.getBody()

				if not _checkUser(u_from):
					log.info("Receive message from unathorized user %s", u_from)
					ch.pushMessage("# You non-auth user!", user=u_from)
					continue;
	
				#do work here
				log.debug("Echo message %s from %s", text, u_from)
				ch.pushMessage(text, user=u_from)
				######
		except Exception as exp:
			_logError("Can't get message: {0}", exp)
		pass
	pass

def fileMessagesLoop():
	global log, ch, send_user_list
	global isReadPipe
	
	if not send_mes_pipe:
		log.info("Message pipe not configured")
		return

	try:
		log.info("Start reading message")

		if len(send_user_list) == 0:
			log.info("No user for message pipe")

		if not os.path.exists(send_mes_pipe):
			log.debug("Create fifo pipe for messages")
			os.mkfifo(send_mes_pipe)
	except Exception as err:
		_logError("Error create message pipe", err)


	while isReadPipe:
		try:
			log.debug("Waiting for message")
			line = file(send_mes_pipe, "r").read()
			if len(line) > 0:
				for us in send_user_list:
					mes = ch.createMessage(line, user=us)
					ch.pushMessage(mes)
			time.sleep(1)
		except Exception as err:
			_logError("Error send mesage from message pipe: {0}", err)
	
	pass

def _checkUser(user):
	global secure_black
	global secure_users

	juser = user
	if type(user) is str:
		juser = xmpp.JID(user) 

	suser = xmpp.JID('vfrc2-notebook@vfrc2.paata.ru')

	print suser.bareMatch(juser)

	print secure_black
	print secure_users
	print [juser]

	if secure_black and not any(u.bareMatch(juser) for u in secure_users):
		return True

	if not secure_black and any(u.bareMatch(juser) for u in secure_users):
		return True

	return False



def _logError(text, exp):
	log.error(text.format(exp))
	log.debug(traceback.format_exc())

if __name__ == "__main__":
	main()