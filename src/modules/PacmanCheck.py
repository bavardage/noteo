import commands
import re

from Noteo import *

class PacmanCheck(NoteoModule):
    no_updates = re.compile('.+no upgrades found.+', re.DOTALL)
    number_of_updates = re.compile('.+Targets \((\d+)\).+', re.DOTALL)
    config_spec = {
        'pollInterval': 'float(default=300)',
        }
    def init(self):
        self.check_event = RecurringFunctionCallEvent(self.noteo,
                                                      self.check,
                                                      self.config['pollInterval']
                                                      )
        self.noteo.add_event_to_queue(self.check_event)

    def check(self):
        status = commands.getoutput('pacman -Qu')
        if not re.match(self.no_updates, status):
            updates = re.match(self.number_of_updates,
                               status,
                               ).groups()[0]
            summary = 'System Updates'
            plural  = (int(updates) > 1)
            message = '%s package%s need%s updating' % (
                updates,
                ('s' if plural else ''),
                ('' if plural else 's')
                )
            notification = NotificationEvent(self.noteo,
                                             0,
                                             summary,
                                             message,
                                             'package-upgrade',
                                             )
            self.noteo.add_event_to_queue(notification)
        return True

module = PacmanCheck
