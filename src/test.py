#!/usr/bin/env python
from Noteo import *

noteo = Noteo()

def spam(*args, **kwargs):
    print "munch munch loverly spam"
    print args
    print kwargs

def irritate(*args, **kwargs):
    print "----------------------------recurring"

class Mod(NoteoModule):
    pass

noteo._modules.append(Mod(noteo))

e = FunctionCallEvent(noteo, 1, spam, 3)
e2 = FunctionCallEvent(noteo, 2, "hi")
e3 = NotificationEvent(noteo, 3, "this is an event", "content", "no icon")

rec = FunctionCallEvent(noteo, 0, irritate)
e4 = RecurringEvent(noteo, rec, 2)

def e3_handled(handlers=None):
    print "event handled by %s" % (handlers)
e3.handled = e3_handled
noteo.add_event_to_queue(e)
noteo.add_event_to_queue(e2)
noteo.add_event_to_queue(e3)
noteo.add_event_to_queue(e4)
noteo.event_loop()
