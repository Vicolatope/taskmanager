from threading import Thread
from taskmaster import Processes
import yaml

class ClientHandler(Thread):
	"""
		The goal for this class is to handle a connection from a 
		client sending command to main TaskManager
	"""
	def __init__(self, lock, connection, processes):
		Thread.__init__(self)
		self.lock = lock
		self.connection = connection
		self.processes = processes
		self.daemon = True

	#start the process specified by line
	def do_start(self, line):
		if line is None:
			self.connection.send('start: argument needed')
			return
		self.lock.acquire()
		try:
			if self.processes[line].status != 'NOT STARTED':
				self.connection.send('%s has already been started' % (line,))
				self.lock.release()
				return
			res = self.processes[line].start()
			self.connection.send(res)
		except:
			self.connection.send('error starting task: ' + line)
		self.lock.release()

	#send status about all the processes
	def do_status(self):
		self.lock.acquire()
		statusInfo = []
		for proc in sorted(self.processes):
			statusInfo.append("%s : %s" % (self.processes[proc].name, self.processes[proc].status,))
		self.connection.send('\n'.join(statusInfo))
		self.lock.release()

	#used to restart a finished process, which can not be restarted using the 'start' command
	def do_restart(self, line):
		if line is None:
			self.connection.send('restart: argument needed')
			return
		self.lock.acquire()
		try:
				res = self.processes[line].restartFromZ()
				self.connection.send(res)
		except:
			self.connection.send('error restarting %s' % (line,))
		self.lock.release()

	"""
	command used to reload a conf_file, some changes will not be permitted if
	the processes concerned by a change of configuration are running
	"""
	def do_reload(self, line):
		if line is None:
			self.connection.send('reload: argument needed')
			return
		try:
			with open(line, 'r') as f:
				data = yaml.load(f)
		except:
			self.connection.send('Problem reloading conf file')
			return
		self.lock.acquire()
		toDel = []
		#iterating through processes to check the one to delete from old conf
		for element in self.processes:
			if element not in data:
				if self.processes[element].status == 'RUNNING' or self.processes[element].status == 'STARTING':
					self.connection.send('Can not remove a running process from the tasklist, stop %s then reload' % (element,))
					return
				else:
					toDel.append(element)

		#iterating to del the one specified
		for key in toDel:
			del self.processes[key]

		#iterating to reload the existing conf and create the new processes instances
		for element in data:
			if element in self.processes:
				self.processes[element].reload(data[element])
			else:
				self.processes[element] = Process(data[element], element)
			try:
				nb_proc = data[element]['running'] - 1
			except:
				nb_proc = 0
			while nb_proc != 0:
				self.processes[element + str(nb_proc + 1)] = Process(data[element], element + str(nb_proc + 1))
				nb_proc -= 1
		self.connection.send('conf file reloaded')
		self.lock.release()
		
	#used to stop the process designated by line
	def do_stop(self, line):
		if line is None:
			self.connection.send('stop: argument needed')
			return
		self.lock.acquire()
		try:
			res = self.processes[line].stop()
			self.connection.send(res)
		except Exception, e:
			self.connection.send( 'error stopping task: %s' % (line,))
		self.lock.release()


	def run(self):
		while 1:
			data = self.connection.recv(4096)
			if len(data) > 0:
				msg = data.split()
				if msg[0] == 'start': self.do_start(' '.join(msg[1:]) if len(msg) > 1 else None)
				elif msg[0] == 'stop': self.do_stop(' '.join(msg[1:]) if len(msg) > 1 else None)
				elif msg[0] == 'reload': self.do_reload(' '.join(msg[1:]) if len(msg) > 1 else None)
				elif msg[0] == 'restart': self.do_restart(' '.join(msg[1:]) if len(msg) > 1 else None)
				elif msg[0] == 'status': self.do_status()
				else: self.connection.send('unknown command')
		return