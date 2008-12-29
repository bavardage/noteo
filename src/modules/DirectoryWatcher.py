import commands
import os

from Noteo import *

class DirectoryWatcher(NoteoModule):
    config_spec = {
        'pollInterval': 'float(default=10.0)',
        'directories': 
        'list(default=list(%s, %s))' % (os.path.expanduser('~'), 
                                        os.path.expanduser('~/Pictures')
                                        )
        }
    items = {}
    def init(self):
        self.update_event = RecurringFunctionCallEvent(self.noteo,
                                                       self.check,
                                                       self.config['pollInterval']
                                                       )
        self.update_event.add_to_queue()
        for directory in self.config['directories']:
            self.items[directory] = self.get_items_in(directory)

    def get_items_in(self, directory):
        return commands.getoutput("ls %s" % directory).split(
            "\n"
            )
        
    def check(self):
        self.noteo.logger.info("Checking directories")
        notifications = []
        for dir in self.config['directories']:
            current_items = self.get_items_in(dir)
            new = []
            gone = []
            self.noteo.logger.info("Current items: %s" % current_items)
            self.noteo.logger.info("Previous items: %s" % self.items[dir])
            for item in current_items:
                if item not in self.items[dir]:
                    new.append(item)
            for item in self.items[dir]:
                if item not in current_items:
                    gone.append(item)
            self.items[dir] = current_items
            if len(new) + len(gone):
                self.noteo.logger.info("new are: %s, gone are %s" % (new, gone))
                self.noteo.logger.info("lens are %s %s" % (len(new), len(gone)))
                message = ""
                if new:
                    message += " <b>Items added:</b> "
                    message += ", ".join(new)
                if gone:
                    if new:
                        message += "\n"
                    message += " <b>Items deleted:</b> "
                    message += ", ".join(gone)
                notifications.append(NotificationEvent(
                        self.noteo,
                        0,
                        "%s changed" % dir,
                        message,
                        'stock_folder'
                        ))
        self.noteo.add_events_to_queue(notifications) #add multiple events to the queue
        return True

module = DirectoryWatcher
