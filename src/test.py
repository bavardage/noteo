#!/usr/bin/env python
from Noteo import *

print Noteo


noteo = Noteo()

e3 = NotificationEvent(noteo, 3, "this is an event", "content", "no icon")
noteo.add_event_to_queue(e3)
noteo.event_loop()
