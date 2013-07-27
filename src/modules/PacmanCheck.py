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
        check_event = FunctionCallEvent(self.check)
        check_event.recurring_delay = self.config['pollInterval']
        self.noteo.add_event(check_event)

    def check(self):
        status = commands.getoutput('pacman -Qu')
        lines = status.count('\n') + 1
        if len(status):
           if lines != self._last_count or \
              (self._reminder == 0 and self.config['iterationsBeforeReminder'] != 0):
               summary = 'System Updates'
               plural  = (lines > 1)
               message = '%s package%s need%s updating' % (
                   lines,
                   ('s' if plural else ''),
                   ('' if plural else 's')
               )
               self.noteo.add_event(NotificationEvent(summary, message, 'system'))
               self._reminder = self.config['iterationsBeforeReminder'] + 1
        self._reminder -= 1
        self._last_count = lines
        return True

module = PacmanCheck
