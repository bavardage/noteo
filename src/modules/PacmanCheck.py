import commands
import re

from Noteo import *

class PacmanCheck(NoteoModule):
    config_spec = {
        'pollInterval': 'float(default=300)',
        'iterationsBeforeReminder': 'integer(default=10)',
        }
    def init(self):
        self._last_count = 0
        self._reminder = 0
        self.check_event = RecurringFunctionCallEvent(self.noteo,
                                                      self.check,
                                                      self.config['pollInterval']
                                                      )
        self.check_event.add_to_queue()

    def check(self):
        status = commands.getoutput('pacman -Qu').split('\n')
        if len(status):
           if len(status) != self._last_count or \
              (self._reminder == 0 and self.config['iterationsBeforeReminder'] != 0):
               summary = 'System Updates'
               plural  = (len(status) > 1)
               message = '%s package%s need%s updating' % (
                   len(status),
                   ('s' if plural else ''),
                   ('' if plural else 's')
               )
               notification = NotificationEvent(self.noteo,
                                                0,
                                                summary,
                                                message,
                                                'system',
                                               )
               notification.add_to_queue()
               self._reminder = self.config['iterationsBeforeReminder'] + 1
        self._reminder -= 1
        self._last_count = len(status)
        return True

module = PacmanCheck
