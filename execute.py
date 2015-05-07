import logging
import time
import threading
import Queue
import subprocess
import os
import stat

class Executer(object):

	log = None
	
	chroot_dir = "./"

	process = None
	popen = None
	run = False

	command_dict = {}

	send_message = None
	command_queue = None

	"""docstring for Executer"""
	def __init__(self, root_for_commands, message_callback=None):
		super(Executer, self).__init__()
		self.log = logging.getLogger(__name__)

		self._initCommands(root_for_commands)

		self.send_message = message_callback
		self.command_queue = Queue.Queue()

		self.run = True
		self.process = threading.Thread(target = self._waitDoCommands)
		self.process.daemon = True
		self.process.start()

		

	def StartExecCommand(self, command, message_callback=None):

		if command == '#!stop':
			if not self.popen:
				return
			else:
				self.popen.terminate()
				return

		if self.popen:
			raise ExecuterAlreadyRunningException()

		if command.split()[0].lower() not in self.command_dict.keys():
			raise ExecuterNoSuchCommandException()
		
		print "callback", message_callback

		self.command_queue.put([self.command_dict[command.lower()], 
			message_callback])
		pass

	def _waitDoCommands(self):

		while self.run:

			try:
				item = self.command_queue.get(timeout=0.2)
				
				cmd = item[0]
				callback = self.send_message
				
				if item[1]:
					callback = item[1]

				self.log.debug("Start exec command %s", cmd[0])

				self.popen = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, \
					stderr=subprocess.STDOUT, cwd=self.chroot_dir, shell=False)

				result = ""

				for line in self.popen.stdout.readlines(): result+=line

				#event )))
				if callback:
					callback(result)

				self.popen = None

				self.log.debug("Stop exec command")

			except Queue.Empty:
				pass
			except Exception as err:
				self.log.error("Command exec error %s",err)
				if callback:
					callback(str(err))

	def _initCommands(self,root_dir):

		self.chroot_dir = root_dir

		executable = stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH

		for filename in os.listdir(root_dir):
			self.log.debug("Find %s", filename)
			filepath = os.path.join(root_dir,filename)
			if os.path.isfile(filepath):
				if filename[0] != '.':
					st = os.stat(filepath)
					mode = st.st_mode

					if mode & executable:
						self.command_dict[filename] = os.path.abspath(filepath)

		self.log.debug("Avalible commands" + str(self.command_dict))



		

class ExecuterAlreadyRunningException(Exception):
	def __init__(self, obj=None):
		super(ExecuterAlreadyRunningException, self).__init__(obj)
	pass

class ExecuterNoSuchCommandException(Exception):
	def __init__(self, obj=None):
		super(ExecuterNoSuchCommandException, self).__init__(obj)
	pass
		