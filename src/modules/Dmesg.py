import commands

from Noteo import *

class Dmesg(NoteoModule):
    config_spec = {
        'pollInterval': 'float(default=10)',
        }
    def init(self):
        self.data = self.get_items()
        self.check_event = RecurringFunctionCallEvent(self.noteo,
                                                      self.check,
                                                      self.config['pollInterval']
                                                      )
        self.check_event.add_to_queue()
    
    def get_items(self):
        return commands.getoutput("dmesg | tail").split("\n")
 
    def check(self):
        messages = self.get_items()
        notifications = []
        for message in messages:
            if message not in self.data:
                notifications.append(NotificationEvent(
                        self.noteo,
                        0,
                        "New Dmesg",
                        message,
                        'dialog-warning'
                        ))
        self.noteo.add_events_to_queue(notifications)
        self.data = messages
        return True
                                
module = Dmesg
