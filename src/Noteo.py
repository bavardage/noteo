#!/usr/bin/env python
# Noteo v 0.1.0
# Copyright Ben Duffield 2008
# Released under the GPL

import time
import logging
from threading import Timer

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
		if callable(self.function):
			return self.function(*self.args, **self.kwargs)
		else:
			self.noteo.logger.warning("Function was not callable")


class NotificationEvent(Event):
	def __init__(self, noteo, due_in, summary, content, icon):
		self.summary = summary
		self.content = content
		self.icon = icon
		super(NotificationEvent, self).__init__(noteo, due_in)
	
	def handle(self):
		self.noteo.send_to_modules(self)


class NoteoModule(object):
	def __init__(self, noteo):
		self.noteo = noteo

	def handle_event(self, event):
		self.noteo.logger.info("Handling event %s" % event)
		return_val = self.do_handle_event(event)
		event.handled()
		return return_val

	def do_handle_event(self, event):
		pass


class Noteo:
	logger = logging
	event_loop_running = False
	event_timer = None
	def __init__(self):
		self.logger.basicConfig(level=logging.DEBUG)
		self._event_queue = []
		self._handled_events = {}
		self._modules = []
	
	def add_event_to_queue(self, event):
		self._event_queue.append(event)
		#self._event_queue.sort()
		self.event_loop()
	
	def event_handled(self, event=None):
		self.logger.info("Event(%s) handled" % event)
		if event in self._handled_events:
			self._handled_events[event][1] -= 1
			if self._handled_events[event][1] <= 0:
				self._handled_events[event][0](event)
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
	
	def handle_event(self, event):
		if time.time() >= event.time:
			self.logger.debug("Handling the event %s" % event)
			event.handle()
			self._event_queue.remove(event)
#			self._event_queue.sort()
		else:
			self.logger.debug("Event not yet due. Procrastinating")
	
	def event_loop(self):
		if self.event_timer:
			self.event_timer.cancel()
			self.event_timer = None
		if not self.event_loop_running:
			self.logger.debug("HANDLING EVENTS")
			self.event_loop_running = True
			for event in self._event_queue:
				self.handle_event(event)
				self._event_queue.sort()
				if not len(self._event_queue):
					self.event_loop_running = False
					return
				else:
					self.logger.info("All pending events handled, sleeping")
					self.logger.info("The event queue now has size %s" %
							 len(self._event_queue))
					sleeptime = self._event_queue[0].time - time.time()
					self.logger.debug("sleeping for %s" % sleeptime)
					if sleeptime > 0:
						self.event_loop_running = False
						if self.event_timer:
							self.event_timer.cancel()
						self.event_timer = Timer(sleeptime, self.event_loop)
						self.event_timer.start()
