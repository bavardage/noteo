#!/usr/bin/env python
# Noteo v 0.1.0
# Copyright Ben Duffield 2008
# Released under the GPL

import time
import logging
from threading import Timer
import os
import sys

from configobj import ConfigObj
from validate import Validator

class NoteoConfig:
	def __init__(self, filename, configspec):
		self.config = ConfigObj(filename, configspec=configspec)
		self.config.validate(Validator(), copy=True)
		self.config.write() #write default values

	def __getitem__(self, field):
		try:
			return self.config[field]
		except(KeyError):
			raise KeyError, field + " is not a valid config option"


class Event(object):
	def __init__(self, noteo, due_in):
		self.noteo = noteo
		self.time = time.time() + due_in
		self.event_id = id(self)
	def handle(self):
		pass

	def handled(self, handler=None):
		pass

	def get_summary(self):
		pass

	def get_content(self):
		pass

	def should_handle(self):
		return True

	def get_icon(self):
		pass
	
	#comparison
	def __lt__(self, other):
		return self.time < other.time
	def __le__(self, other):
		return self.time <= other.time
	def __eq__(self, other):
		return self.time == other.time
	def __ne__(self, other):
		return self.time != other.time
	def __gt__(self, other):
		return self.time > other.time
	def __ge__(self, other):
		return self.time >= other.time
	#representations
	def __repr__(self):
		return "%s %s" % (self.__class__.__name__, self.event_id)


class FunctionCallEvent(Event):
	def __init__(self, noteo, due_in, function, *args, **kwargs):
		self.function = function
		self.args = args
		self.kwargs = kwargs
		super(FunctionCallEvent, self).__init__(noteo, due_in)

	def handle(self):
		return_value = None
		if callable(self.function):
			return_value = self.function(*self.args, **self.kwargs)
		else:
			self.noteo.logger.warning("Function was not callable")
		self.handled()
		return return_value


class NotificationEvent(Event):
	def __init__(self, noteo, due_in, summary, content, icon):
		self.summary = summary
		self.content = content
		self.icon = icon
		super(NotificationEvent, self).__init__(noteo, due_in)
	
	def handle(self):
		self.noteo.send_to_modules(self)

class RecurringEvent(Event):
	def __init__(self, noteo, recurring_event, interval):
		self.event = recurring_event
		self.event_handled = self.event.handled
		self.event.handled = self.handled
		self.interval = interval
		super(RecurringEvent, self).__init__(noteo, 0)
	
	def handle(self):
		self.noteo.logger.info("adding recurring event to queue")
		self.event.time = time.time() + self.interval
		self.noteo.add_event_to_queue(self.event)

	def handled(self, handlers=None):
		self.handle()

class NoteoModule(object):
	'''NoteoModule is used to provide most of noteo's functionality
	This should not be used by itself, but used as a super class'''
	config_spec = {}
	def __init__(self, noteo, path=""):
		self.noteo = noteo
		self.modulename = self.__class__.__name__
		self.path = path
		self.configure()
		self.init()

	def init(self):
		'''init()
		You should overload this instead of providing an __init__ function
		By the time init() is called, everything should work properly.'''
		pass

	def configure(self):
		config_path = os.path.join(self.noteo.config_dir, self.__class__.__name__)
		self.config = NoteoConfig(config_path, self.config_spec)
		
	def handle_event(self, event):
		self.noteo.logger.info("Handling event %s" % event)
		return_val = self.do_handle_event(event)
		event.handled()
		return return_val

	def do_handle_event(self, event):
		'''do_handle_event(event)
		overload this when you want to do something with the event,
		but the event is handled straight away - you will usually want to
		do this. Overload handle_event when you want more control'''
		pass
	
	def event_is_invalid(self, event):
		'''event_is_invalid(event)
		this is called when an event is made invalid before it is due to be
		called. If the event doesn't exist, then this should gracefully do 
		nothing'''
		pass

class Noteo:
	logger = logging
	#event loop stuff
	event_loop_running = False
	event_timer = None
	#module, paths, etc
	local_module_dir = os.path.expandvars('$HOME/.noteo')
	module_dir = '/usr/share/noteo/'
	config_dir = os.path.expandvars('$HOME/.config/noteo')
	def __init__(self):
		self.logger.basicConfig(level=logging.DEBUG)
		self._event_queue = []
		self._handled_events = {}
		self._modules = []
		self._configure()
		self._load_modules()
	
	#configuration
	def _configure(self):
		try:
			os.makedirs(Noteo.config_dir)
		except:
			self.logger.debug("Noteo configuration directory already exists")
		config_spec = {
			'localmodules': 'list(default=list(\'Test\'))',
			'modules': 'list(default=list(\'RemoteTest\'))',
			}
		config_path = os.path.join(Noteo.config_dir, 'Noteo')
		self.config = NoteoConfig(config_path, config_spec)

	#modules
	def _load_modules(self):
		for module_name in self.config['modules']:
			self._load_module(module_name, local=False)
		for module_name in self.config['localmodules']:
			self._load_module(module_name, local=True)
	
	def _load_module(self, module_name, local=False):
		if local:
			path = os.path.join(Noteo.local_module_dir, module_name)
		else:
			path = os.path.join(Noteo.module_dir, module_name)
		sys.path.append(path)
		try:
			module = __import__(module_name).module(self, path)
			self._modules.append(module)
		except:
			self.logger.error("An error occured when importing the module %s"
					  % module_name)
		finally:
			sys.path.pop()

	#events
	def add_event_to_queue(self, event):
		self._event_queue.append(event)
		self.event_loop()
	
	def event_handled(self, event=None):
		self.logger.info("Event(%s) handled" % event)
		if event in self._handled_events:
			self._handled_events[event][1] -= 1
			if self._handled_events[event][1] <= 0:
				self._handled_events[event][0]()
				del self._handled_events[event][0]
		else:
			self.logger.error("Event was not in _handled_events")
		
	def send_to_modules(self, event):
		handled = event.handled
		def new_handled():
			self.event_handled(event)
		event.handled = new_handled
		self._handled_events[event] = [handled, 0]
		for module in self._modules:
			self._handled_events[event][1] += 1
			module.handle_event(event)
			
	def invalidate_to_modules(self, event):
		for module in self._modules:
			module.event_is_invalid(event)
	
	def handle_event(self, event):
		if time.time() >= event.time:
			self.logger.debug("Handling the event %s" % event)
			event.handle()
			self._event_queue.remove(event)
#			self._event_queue.sort()
		else:
			self.logger.debug("Event not yet due. Procrastinating")
	
	def event_loop(self):
		eq = self._event_queue
		self.logger.debug("Entering event_loop")
		if self.event_loop_running:
			return
		self.event_loop_running = True
		if self.event_timer is not None:
			#if there is currently a timer going, kill it!
			self.event_timer.cancel()
			self.event_timer = None
		for e in eq:
			self.handle_event(e)
		eq.sort()
		if len(eq):
			wait_time = eq[0].time - time.time()
			if wait_time <= 0:
				wait_time = 0
			self.event_timer = Timer(wait_time, self.event_loop)
			self.event_timer.start()
			self.logger.debug("Started a timer with delay of %s" % wait_time)
			self.event_loop_running = False
		else:
			self.logger.debug("No events to handle. \
Exiting event_loop")
			self.event_loop_running = False
		
