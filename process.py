import cmd
import sys
import os
from stat import *
import logging
import subprocess
import signal
import time

log = logging
log.basicConfig(filename='/tmp/task_logging', level=logging.DEBUG)

class Process:

	def data_load(self):
		data = self.data
		self.pid = None
		self.process = None
		self.status = 'NOT STARTED' if hasattr(self, 'status') == False else self.status
		self.retcode = None

		# the command used to launch the program !needed
		if 'command' in data:
			self.command = data['command'];
			self.args = self.command.split()
		else:
			self.error_logging('No command in ' + name + ' config file')
			return
		# set outputs for the process
		self.stdout = data['stdout'] if 'stdout' in data else None
		self.stderr = data['stderr'] if 'stderr' in data else None

		#set the workdir for the proc
		self.workingdir = data['workingdir'] if 'workingdir' in data else None

		# if set, the program starts at launch
		self.autostart = data['autostart'] if 'autostart' in data else 0

		#modify the rocess environment variables through the config file
		if 'env' in data:
			self.env.update(data['env'])

		#choose if a proc should be restarted -> never, always or only on unexpected
		self.restart = data['restart'] if 'restart' in data else 'unexpected'

		#set the 'expected'	return codes
		self.returncodes = data['returncodes'] if 'returncodes' in data else (0, 2)

		#set the number of restart to attempt before aborting, default is 3
		self.restartnb = data['restartnb'] if 'restartnb' in data else 3

		#signal to use for gracefullstop, default is SIG_TERM
		self.signal = data['signal'] if 'signal' in data else None

		#time to wait after a gracefull stop before killing the program
		self.gracefullstop = data['gracefullstop'] if 'gracefullstop' in data else 10

		# set the number of instances of the prog to keep running at the same time
		self.running = data['running'] if 'running' in data else None

		#set the time for the program to pass from STARTING to RUNNING
		self.successtart = data['successtart'] if 'successtart' in data else None

		#set an umask for the file creation
		self.umask = data['umask'] if 'umask' in data else 022

	def __init__(self, data, name):

		self.name = name
		self.data = data
		self.startime = None
		self.env = os.environ.copy()
		self.data_load()

	def data_check(self, to_check, data):
		if to_check in data and data[to_check] != self.data[to_check]:
			return False
		return True


	def reload(self, data):
		if self.status == 'RUNNING' or self.status == 'STARTING':
			if self.data_check('env', data) or \
				self.data_check('stdin', data) or \
				self.data_check('stdout', data) or \
				self.data_check('workingdir', data) or \
				self.data_check('command', data) or \
				self.data_check('running', data):
				res = '%s configuration can not be changed, it is running, stop it first' % (self.name,)
				self.warning_logging(res)
				return res
		self.data = data
		self.data_load()


		

	def check_workingdir(self):
		if os.path.isdir(self.workingdir) and os.access(self.workingdir, os.W_OK):
			return (self.workingdir)
		else:
			self.warning_logging("couldn't work in " + self.workingdir)
			return None


	def check_file(self, file):
		oldmask = os.umask(self.umask)
		try:
			f = open(file, 'w+')
			return f
		except:
			os.umask(oldmask)
			if file:
				self.warning_logging("couldn't open file " + file)
			return None

	def retcodeToStat(self):
		retcode = -self.retcode if self.retcode < 0 else self.retcode
		self.status = {True: 'FINISHED',
			retcode == signal.SIGTERM : 'TERMINATED',
			retcode == signal.SIGKILL : 'KILLED',
			retcode == signal.SIGINT : 'INTERRUPTED'}[True]

	def update(self):

		if self.status == 'STARTING':
			if (time.time() - self.startime) > self.successtart:
				self.status = 'RUNNING'

		if self.status == 'RUNNING' or self.status == 'STARTING':
			if self.process.poll() is not None:
				self.retcode = self.process.returncode
				# print self.retcode
				self.status = 'FINISHED'
				if self.retcode not in self.returncodes or self.restart == 'always':
					if self.restart == 'unexpected' or self.restart == 'always':
						if self.restartnb > 0:
							self.restartnb = self.restartnb - 1
							self.start()
							log.info('restarting %s, %s' % (self.name, 'non expected retcode' if self.restart == 'unexpected' else 'it should always restart',))
						else:
							self.status == 'FATAL'
							self.warning_logging('%s can not be started as you planned, aborting' % (self.name,))
				else:
					self.retcodeToStat()

		if self.status == 'STOPPING':
			if self.process.poll() is not None:
				self.retcode = self.process.returncode
				self.retcodeToStat()
				log.info('successfully stopped %s' % (self.name,))
			elif (time.time() - self.stoptime) > self.gracefullstop:
				os.kill(self.pid, signal.SIGKILL)
				self.status = 'KILLED'
				self.warning_logging('%s can not be stooped, killing it' % (self.name,))


					
	def restartFromZ(self):
		if self.status == 'NOT STARTED' or self.status == 'STARTING' or self.status == 'RUNNING':
			res = '%s can not restart, let him finish first' % (self.name,)
			self.warning_logging(res)
			return res
		else:
			try:
				self.data_load()
				self.start()
				res = 'restarted %s' % (self.name,)
				log.info(res)
				return res
			except:
				res = '%s couldn\'t be restarted' % (self.name,)
				self.warning_logging(res)
				return res


	def stop(self):

		if self.status == 'RUNNING' or self.status == 'STARTING':
			try:
				self.status = 'STOPPING'
				os.kill(self.pid, self.signal if self.signal else signal.SIGTERM)
				self.stoptime = time.time()
				res = 'stopping %s' % (self.name,)
				log.info(res)
				return res
			except:
				os.kill(self.pid, signal.SIGKILL)
				res = '%s can not be stooped, killing it' % (self.name,)
				self.warning_logging(res)
				self.status = 'KILLED'
				return res
		else:
			res = '%s can not be stooped, it may not be running yet' % (self.name,)
			self.warning_logging(res)
			return res


	def start(self):

		try:
			self.process = subprocess.Popen(self.args,
				stdout=self.check_file(self.stdout),
				stderr=self.check_file(self.stderr),
				env=self.env,
				cwd=self.check_workingdir() if self.workingdir else None
			)
			self.pid = self.process.pid
			self.startime = time.time()
			res = 'started %s' % (self.name,)
			log.info(res)
			if self.successtart != None:
				self.status = 'STARTING'
			else:
				self.status = 'RUNNING'
			return res
		except:
			res = "could not start %s" % (self.name,)
			self.warning_logging(res)
			return res


	def warning_logging(self, warning):
		print 'Warning during execution: ' + warning
		log.warning(warning)

	def error_logging(self, error):
		print 'Error during execution: ' + error
		log.error('Error during execution: ' + error)
		sys.exit(0)
				


