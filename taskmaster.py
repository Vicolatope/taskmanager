#!/usr/bin/python

from process import *
from clientHandler import *
import os
import sys
import yaml
import subprocess
from threading import Thread, Lock
import socket

Processes = {}

class StatusThread(Thread):

	def __init__(self, lock, name):
		Thread.__init__(self)
		self.name = name
		self.daemon = True
		self.lock = lock

	def run(self):
		global Processes

		while 1:
			self.lock.acquire()
			for key in Processes:
				Processes[key].update()
			self.lock.release()

def init_task(file_name):

	try:
		with open(file_name, 'r') as f:
			data = yaml.load(f)
	except:
		print 'Problem loading conf file'
		log.error('Problem loading conf file')
		sys.exit(0)

	for element in data:
		try:
			nb_proc = data[element]['running']
		except:
			nb_proc = 1
		while nb_proc != 1:
			Processes[element + str(nb_proc)] = Process(data[element], element + str(nb_proc))
			nb_proc -= 1
		Processes[element] = Process(data[element], element)
		for element in Processes:
			if Processes[element].autostart == 1:
				Processes[element].start()

if __name__ == '__main__':
	if len(sys.argv) != 2:
		print >>sys.stderr, 'usage: ./taskmaster.py conf_file'
		sys.exit(1)
	PLock = Lock()
	init_task(sys.argv[1])
	myStatusThread = StatusThread(PLock, 'mythread')
	myStatusThread.start()
	supervisorServer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	server_addr = '/tmp/supersocket'
	try:
		os.unlink(server_addr)
	except:
		if os.path.exists(server_addr):
			raise
	supervisorServer.bind(server_addr)
	supervisorServer.listen(1)
	clients = {}
	while True:
		connection, client_addr = supervisorServer.accept()
		clients[client_addr] = ClientHandler(lock=PLock, connection=connection, processes=Processes)
		clients[client_addr].start()
	# Prompt(PLock).cmdloop()
