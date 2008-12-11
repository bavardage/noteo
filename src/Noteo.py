#!/usr/bin/env python
# Noteo v 0.1.0
# Copyright Ben Duffield 2008
# Released under the GPL

import time
import logging
import os
import sys
import gtk

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

def get_icon(icon, size=64):
	'''get_icon(size=64)
	uses the value of self.icon
	if self.icon is an icon, then this is simply returned
	if icon is a path to an image, this image is loaded and returned,
	if icon is a string, this is looked up as a gtk icon
	returns a gtk.gdk.Pixbuf if an icon can be found, or None otherwise'''
	if isinstance(icon, gtk.gdk.Pixbuf):
		return icon
	elif os.path.exists(icon):
		return gtk.gdk.pixbuf_new_from_file_at_size(icon, size, size)
	else:
		icon_theme = gtk.icon_theme_get_default()
		if icon_theme.has_icon(icon):
			try:
				return icon_theme.load_icon(icon, size, 0)
			except:
				return None
		return None

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
		return get_icon(self.icon, size)

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

class CreateMenuItemEvent(Event):
	def __init__(self, noteo, label, callback, icon=None):
		self.label = label
		self.callback = callback
		self.icon = icon
		super(CreateMenuItemEvent, self).__init__(noteo, 0)
	
	def get_icon(self, size=64):
		return get_icon(self.icon, size)
	
	def handle(self):
		self.noteo.send_to_modules(self)

class QuitEvent(Event):
	def __init__(self, noteo, quit_in):
		super(QuitEvent, self).__init__(noteo, quit_in)

	def handle(self):
		try:
			gtk.main_quit()
		except:
			pass
		sys.exit(0)

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
			if name == 'Event':
				return default_handle_event(event)
			elif hasattr(self, "handle_%s" % name):
				return getattr(self, "handle_%s" % name)(event)
			elif hasattr(self, "do_handle_%s" % name):
				return_val = getattr(self, "do_handle_%s" % name)(event)
				event.handled(event)
				return return_val
		self.noteo.logger.error("Reached end of handle_event in %s, this probably shouldn't happen" % self.modulename)
		self.noteo.logger.error("Event had type: %s, mro of (%s)" % (event.__class__.__name__, event.__class__.mro()))
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
		self.queue.sort()

	def __repr__(self):
		output = []
		for e in self.queue:
			output.append(str(time.time() - e.time))
		return ", ".join(output)

class Noteo:
	logger = logging
	#event loop stuff
	event_loop_running = False
	event_timer = None
	#gtk
	gtk_is_required = False
	#module, paths, etc
	local_module_dir = os.path.expandvars('$HOME/.noteo')
	module_dir = '/usr/share/noteo/modules/'
	config_dir = os.path.expandvars('$HOME/.config/noteo')
	def __init__(self, load_modules = True):
		self._configure()
		self._event_queue = EventQueue()
		self._handled_events = {}
		self._to_add_to_queue = []
		self._modules = []
		if load_modules:
			self._load_modules()
	
	#configuration
	def _configure(self):
		try:
			os.makedirs(Noteo.config_dir)
		except:
			#self.logger.debug("Noteo configuration directory already exists")
			pass
		config_spec = {
			'localmodules': 'list(default=list(\'\'))',
			'modules': 'list(default=list(BatteryCheck, Dmesg, Awesome, GmailCheck, Xmms2, MPD, DirectoryWatcher, StatusIcon, Notify, Popup))',
			'threadGTK': 'boolean(default=False)',
			'debugLevel': 'integer(default=30)', #logger.WARNING = 30 
			}
		config_path = os.path.join(Noteo.config_dir, 'Noteo')
		self.config = NoteoConfig(config_path, config_spec)
		self.logger.basicConfig(level=self.config['debugLevel'])
		print "logging initialised for debug level %s" % self.config['debugLevel']

	#modules
	def _load_modules(self):
		self.logger.info("Loading modules")
		for module_name in self.config['modules']:
			self._load_module(module_name, local=False)
		for module_name in self.config['localmodules']:
			self._load_module(module_name, local=True)
	
	def _load_module(self, module_name, local=False):
		if local:
			path = Noteo.local_module_dir
		else:
			path = Noteo.module_dir
		sys.path.append(path)
		try:
			module = __import__(module_name).module(self, path)
			self._modules.append(module)
		except:
			self.logger.error("Errors occured when importing the module %s"
					  % module_name)
			self.logger.error("The error were: %s" % str(sys.exc_info()))
			#raise
		finally:
			sys.path.pop()

	#events
	def add_event_to_queue(self, event):
		self._event_queue.push(event)
		#self.event_loop()
		#self.gtk_update()
	
	def add_events_to_queue(self, events):
		self._event_queue.extend(events)
		#self.event_loop()
		#self.gtk_update()
	
	def event_handled(self, event):
		self.logger.info("Event(%s) handled" % event)
		if event in self._handled_events:
			self._handled_events[event][1] -= 1
			if self._handled_events[event][1] <= 0:
				self._handled_events[event][0](event)
				del self._handled_events[event]
		else:
			self.logger.error("Event was not in _handled_events")
		#self.gtk_update()
		
	def send_to_modules(self, event):
		self.logger.debug("Sending event(%s) to modules" % event)
		handled = event.handled
		def new_handled(event):
			self.event_handled(event)
		event.handled = new_handled
		self._handled_events[event] = [handled, len(self._modules)]
		for module in self._modules:
			module.handle_event(event)
		#self.gtk_update()
			
	def invalidate_to_modules(self, event):
		for module in self._modules:
			module.event_is_invalid(event)
	
	def handle_event(self, event):
		self.logger.debug("in handle_event for event(%s)" % event)
		event.handle()
	
	def event_loop(self):
		while True:
			eq = self._event_queue
			self.logger.debug("Entering event_loop")
			while eq.peek() and eq.peek().time <= time.time():
				self.handle_event(eq.pop())
			#self.gtk_update()
			if not eq.peek():
				self.logger.warning("No events to handle - exiting")
				return
			else:
				wait_time = eq.peek().time - time.time()
				if wait_time > 0:
					self.logger.info("Sleeping for %.3f" % wait_time)
					time.sleep(wait_time)
	
	def gtk_required(self):
		self.logger.debug("GTK is required")
		self.logger.debug("Already required? %s" % self.gtk_is_required)
		if not self.gtk_is_required:
			if self.config['threadGTK']:
				from threading import Timer
				gtk.gdk.threads_init()
				t = Timer(0.1, gtk.main)
				t.start()
			else:
				self.logger.debug("Not already set-up. Setting up...")
				event = RecurringFunctionCallEvent(
					self,
					self.gtk_update,
					0.1)
				self.add_event_to_queue(event)
		self.gtk_is_required = True

	def gtk_update(self):
		while gtk.events_pending():
			gtk.main_iteration()
		return True
		

if __name__ == '__main__':
	print "running noteo..."
	noteo = Noteo()
	noteo.event_loop()
	print "done..."
