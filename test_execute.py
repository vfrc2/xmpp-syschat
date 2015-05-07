import execute
import logging

logging.basicConfig(level=logging.DEBUG)

def printMessage(text):
	print text

exe = execute.Executer("./bin", printMessage)

print "Executer test"

while True:
	try:
		line = raw_input()
		exe.StartExecCommand(line)
	except execute.ExecuterAlreadyRunningException as err:
		print "Already executing... To stop enter #!stop"
	except execute.ExecuterNoSuchCommandException as err:
		print "No such command... try help"





