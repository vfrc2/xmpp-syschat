
import logging
import traceback
import Queue
import xmpp
import command
import threading



class SysChat():

	log = None

	client = None

	server_url="localhost"
	server_port="5222"

	user=xmpp.JID("user@localhost")
	password="1234"

	send_to=xmpp.JID("recivier@localhost")
	send_to_group = None

	sendLock = None

	send_queue = None
	receive_queue = None

	noError = True
	error = None
	
	def __init__(self):
		self.log = logging.getLogger("syschat")
		pass

	def connectAndAuth(self):

		self.send_queue = Queue.Queue()
		self.receive_queue = Queue.Queue()
		self.sendLock = threading.RLock()

		self.noError = True
		self.error = None

		self.log.info("Connecting to %s:%s",self.server_url,self.server_port)

		if not self.client:
			self.client = xmpp.Client(self.server_url)

		if 'tcp' != self.client.connect(
			server=(self.server_url,self.server_port)
			,secure=0
			):
			raise Exception("Unknown connection error")

		self.log.debug("Auth with %s", self.user)
		self.client.auth(self.user.getNode(), self.password, sasl=0)
		self.client.sendInitPresence()
		pass

	def startChat(self):
		
		self.client.RegisterHandler('message', self._receiveXmppMessage)

		processLoop = threading.Thread(target=self._processLoop)
		processLoop.daemon = True
		processLoop.start()
		
		sendLoop = threading.Thread(target=self._sendMessageLoop)
		sendLoop.daemon = True
		sendLoop.start();
	
	
	def pushMessage(self, message, user=None):

		mes = message

		if type(message) != xmpp.Message:
			mes = self.createMessage(message, user=user)

		self.log.debug("Push message %s",mes.getBody())
		self.send_queue.put(mes)

		pass

	def getMessage(self, timeout=None):
		try:
			mess = self.receive_queue.get(timeout = timeout)
			self.log.debug("Getting message")
			return mess 
		except Queue.Empty:
			return None
	
	def createMessage(self, text, user = None):

		if not user:
			if self.send_to:
				user = self.send_to

		self.log.debug("Create  mes for %s", user.getNode())
		mes = xmpp.Message(user, text)
		mes.setAttr('type', 'chat')

		return mes

	def close(self):
		try:
			self.send_queue = None
			self.receive_queue = None
			self.sendLock = None

			self.noError = False
			self.error = None
		except Exception as err:
			self.log.error("Error while close %s", err)
			self.log.debug(traceback.format_exc())

	def _registrateError(self, error):
		self.log.error(error)
		self.log.debug(traceback.format_exc())
		self.error = error
		self.noError = False

	def _receiveXmppMessage(self, session, message):
		self.log.debug("Receive message")
		self.receive_queue.put(message);

	def _sendMessageLoop(self):
		while self.noError:
			try:
				mes = self.send_queue.get(timeout=0.1)
				self.log.debug("Send message %s to %s",mes.getBody(), mes.getTo())
				self.client.send(mes)
			except Queue.Empty:
				pass
			except Exception as err:
				self._registrateError(err)
			pass

	def _processLoop(self):
		try:
			while self.noError:
				self.client.Process(1)
		except Exception as err:
			self._registrateError(err)

	


	pass


