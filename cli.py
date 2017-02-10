import sys
import socket
import readline
import fcntl
import sys

def displayHelp():
	print >> sys.stderr, 'This is a taskmaster client used to send instructions to a running instance of taskmaster server'
	print >> sys.stderr, 'Theese are the different commands to use:'
	print >> sys.stderr, '-> start process_name: start the named process if hasn\'t started yet'
	print >> sys.stderr, '-> stop process_name: stop the named process if running'
	print >> sys.stderr, '-> status: show the status of all the processes listed in the conf_file'
	print >> sys.stderr, '-> restart: restart a process that\'s already finished'
	print >> sys.stderr, '-> reload conf_file: reload a conf_file, some modifications require the process not to be running'


def commandLoop():
	while True:
		try:
			data = raw_input('>>')
			if data == 'exit':
				sock.close()
				sys.exit(0)
			elif data == 'help':
				displayHelp()
			else:
				sock.sendall(data)
				data_r = sock.recv(4096)
				print >> sys.stderr, data_r
		except socket.error:
			print >> sys.stderr, 'Error reaching the TaskServer, please verify there is an instance running'

if __name__ == '__main__':
	sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	server_addr = '/tmp/supersocket'
	try:
		sock.connect(server_addr)
	except socket.error, msg:
		print >>sys.stderr, 'Error reaching the TaskServer, please verify there is an instance running'
		sys.exit(1)
	commandLoop()

