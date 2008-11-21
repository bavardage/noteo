#!/usr/bin/env python
from Noteo import *

noteo = Noteo()

e = FunctionCallEvent(noteo, lambda x:x*x, 3)
print e.handle()
e2 = FunctionCallEvent(noteo, "hi")
print e2.handle()
