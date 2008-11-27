#!/usr/bin/env python
# Noteo v 0.1.0
# Copyright Ben Duffield 2008
# Released under the GPL

import time
import logging
from threading import Timer
import os
import sys
import gtk
import heapq

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

	def handled(self, event, handler=None):
		pass

	def should_handle(self):
		return True
	
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
		self.handled(self)
		return return_value


class NotificationEvent(Event):
	def __init__(self, noteo, due_in, summary, content, icon="", timeout=-1, handled=None):
		self.summary = summary
		self.content = content
		self.icon = icon
		self.timeout = timeout
		self.on_handled = handled
		super(NotificationEvent, self).__init__(noteo, due_in)
	
	def handle(self):
		self.noteo.send_to_modules(self)

	def handled(self, event, handlers=None):
		if callable(self.on_handled):
			self.on_handled(event)

	def __repr__(self):
		return '"%s" "%s" "%s"' % (self.summary, self.content, self.icon)

	def get_summary(self):
		return str(self.summary)
	
	def get_content(self):
		return str(self.content)

	def get_icon(self, size=64):
		'''get_icon(size=64)
		uses the value of self.icon
		if self.icon is an icon, then this is simply returned
		if icon is a path to an image, this image is loaded and returned,
		if icon is a string, this is looked up as a gtk icon
		returns a gtk.gdk.Pixbuf if an icon can be found, or None otherwise'''
		if isinstance(self.icon, gtk.gdk.Pixbuf):
			return self.icon
		elif os.path.exists(self.icon):
			return gtk.gdk.pixbuf_new_from_file_at_size(self.icon, size, size)
		else:
			icon_theme = gtk.icon_theme_get_default()
			if icon_theme.has_icon(self.icon):
				try:
					return icon_theme.load_icon(self.icon, size, 0)
				except:
					return None
		return None

	def get_timeout(self):
		return self.timeout

class RecurringEvent(Event):
	def __init__(self, noteo, recurring_event, interval):
		self.event = recurring_event
		self.event_handled = self.event.handled
		self.event.handled = self.handled
		self.interval = interval
		super(RecurringEvent, self).__init__(noteo, 0)
	
	def handle(self):
		self.noteo.logger.debug("adding recurring event to queue")
		self.event.time = time.time() + self.interval
		self.noteo.add_event_to_queue(self.event)

	def handled(self, event, handlers=None):
		self.event_handled(self)
		self.handle()

class RecurringFunctionCallEvent(Event):
	def __init__(self, noteo, function, interval):
		self.function = function
		self.interval = interval
		super(RecurringFunctionCallEvent, self).__init__(noteo, interval)

	def handle(self):
		self.noteo.logger.debug("Calling recurring function")
		return_value = None
		if callable(self.function):
			return_value = self.function()
		if return_value:
			self.time = time.time() + self.interval
			self.noteo.add_event_to_queue(self)
		return return_value

class NoteoModule(object):
	'''NoteoModule is used to provide most of noteo's functionality
	This should not be used by itself, but used as a super class'''
	config_spec = {}
	def __init__(self, noteo, path=""):
		self.noteo = noteo
		self.modulename = self.__class__.__name__
		self.noteo.logger.info("Initialising module %s" % self.modulename)
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
		superclasses = event.__class__.mro()
		def default_handle_event(event):
			self.noteo.logger.info("Handling event %s with default handler" % event)
			return_val = self.do_handle_event(event)
			event.handled(event)
			return return_val
		for supercls in superclasses:
			name = supercls.__name__
			if name == 'event':
				return handle_event(event)
			elif hasattr(self, "handle_%s" % name):
				return getattr(self, "handle_%s" % name)(event)
			elif hasattr(self, "do_handle_%s" % name):
				return_val = getattr(self, "do_handle_%s" % name)(event)
				event.handled(event)
				return return_val
		self.noteo.logger.error("Reached end of handle_event in %s, this probably shouldn't happen" % self.modulename)
		return None

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

class EventQueue:
	def __init__(self):
		self.queue = []
	
	def peek(self):
		try:
			return self.queue[0]
		except:
			return False

	def pop(self):
		try:
			item = self.queue[0]
			self.remove(item)
			return item
		except:
			return False

	def push(self, item):
		self.queue.append(item)
		self.queue.sort()

	def extend(self, items):
		self.queue.extend(items)
		self.queue.sort()

	def remove(self, item):
		self.queue.remove(item)

class Noteo:
	logger = logging
	#event loop stuff
	event_loop_running = False
	event_timer = None
	#module, paths, etc
	local_module_dir = os.path.expandvars('$HOME/.noteo')
	module_dir = '/usr/share/noteo/'
	config_dir = os.path.expandvars('$HOME/.config/noteo')
	def __init__(self, load_modules = True):
		self.logger.basicConfig(level=logging.DEBUG)
		self._event_queue = EventQueue()
		self._handled_events = {}
		self._to_add_to_queue = []
		self._modules = []
		self._configure()
		if load_modules:
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
		self.logger.info("Loading modules")
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
			self.logger.error("Errors occured when importing the module %s"
					  % module_name)
			self.logger.error("The error were: %s" % str(sys.exc_info()))
			raise
		finally:
			sys.path.pop()

	#events
	def add_event_to_queue(self, event):
		self._event_queue.push(event)
		self.event_loop()
		self.gtk_update()
	
	def add_events_to_queue(self, events):
		self._event_queue.extend(events)
		self.event_loop()
		self.gtk_update()
	
	def event_handled(self, event):
		self.logger.info("Event(%s) handled" % event)
		if event in self._handled_events:
			self._handled_events[event][1] -= 1
			if self._handled_events[event][1] <= 0:
				self._handled_events[event][0](event)
				del self._handled_events[event]
		else:
			self.logger.error("Event was not in _handled_events")
		self.gtk_update()
		
	def send_to_modules(self, event):
		self.logger.debug("Sending event(%s) to modules" % event)
		handled = event.handled
		def new_handled(event):
			self.event_handled(event)
		event.handled = new_handled
		self._handled_events[event] = [handled, len(self._modules)]
		for module in self._modules:
			module.handle_event(event)
		self.gtk_update()
			
	def invalidate_to_modules(self, event):
		for module in self._modules:
			module.event_is_invalid(event)
	
	def handle_event(self, event):
		self.logger.debug("in handle_event for event(%s)" % event)
		event.handle()
	
	def event_loop(self):
		eq = self._event_queue
		self.logger.debug("Entering event_loop")
		if self.event_loop_running:
			return
		self.event_loop_running = True
		if self.event_timer is not None:
			#if there is currently a timer going, kill it!
			self.logger.debug("Killing timer (%s)" % self.event_timer)
			self.event_timer.cancel()
			self.event_timer = None
		while eq.peek() and eq.peek().time <= time.time():
			self.handle_event(eq.pop())
		self.gtk_update()
		if eq.peek():
			wait_time = eq.peek().time - time.time()
			if wait_time > 0:
				self.event_timer = Timer(wait_time, self.event_loop)
				self.event_timer.start()
				self.logger.debug("Started a timer (%s) with delay of %s" % (self.event_timer, wait_time))
				self.event_loop_running = False
			else:
				self.event_loop_running = False
				self.event_loop()
				return
		else:
			self.logger.debug("No events to handle. \
Exiting event_loop")
			self.event_loop_running = False
	
	def gtk_update(self):
		while gtk.events_pending():
			gtk.main_iteration()
		return True
		
