#!/usr/bin/env python
from Noteo import *

noteo = Noteo()

def spam(*args, **kwargs):
    print "munch munch loverly spam"
    print args
    print kwargs

class Mod(NoteoModule):
    pass

noteo._modules.append(Mod(noteo))

e = FunctionCallEvent(noteo, 1, spam, 3)
e2 = FunctionCallEvent(noteo, 2, "hi")
e3 = NotificationEvent(noteo, 3, "this is an event", "content", "no icon")
def e3_handled(event, handlers=None):
    print "event(%s) handled by %s" % (event, handlers)
e3.handled = e3_handled
noteo.add_event_to_queue(e)
noteo.add_event_to_queue(e2)
noteo.add_event_to_queue(e3)
noteo.event_loop()
