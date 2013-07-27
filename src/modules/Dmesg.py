import commands

from Noteo import *

class Dmesg(NoteoModule):
    config_spec = {'pollInterval': 'float(default=10)'}
    def init(self):
        self.data = self.get_items()
        check_event = FunctionCallEvent(self.check)
        check_event.recurring_delay = self.config['pollInterval']
        self.noteo.add_event(check_event)

    def get_items(self):
        return commands.getoutput("dmesg | tail").split("\n")
 
    def check(self):
        messages = self.get_items()
        notifications = []
        for message in messages:
            if message not in self.data:
                self.noteo.add_event(NotificationEvent("New Dmesg",
                                                       message,
                                                       'dialog-warning'))
        self.data = messages
        return True

module = Dmesg
