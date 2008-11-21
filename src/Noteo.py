#!/usr/bin/env python
# Noteo v 0.1.0
# Copyright Ben Duffield 2008
# Released under the GPL

import time
import logging


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
	def handle(self):
		pass

	def handled(self, handler):
		pass

	def get_summary(self):
		pass

	def get_content(self):
		pass

	def should_handle(self):
		return True

	def get_icon(self):
		pass

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
	def __init__(self, due_in, summary, content, icon):
		self.summary = summary
		self.content = content
		self.icon = icon
		super(NotificationEvent, self).__init__(noteo, due_in)


	
class Noteo:
	logger = logging
	def __init__(self):
		self.logger.basicConfig()
		self._eventQueue = []
	def add_event_to_queue(event):
		self._eventQueue.append(event)
		self._eventQueue.sort()
