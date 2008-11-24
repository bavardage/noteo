import commands

from Noteo import *

class Xmms2(NoteoModule):
    config_spec = {
        'pollInterval': 'float(default=2.0)',
        }
    def init(self):
        self.current_song = self.get_current_song()
        self.update_event = RecurringFunctionCallEvent(self.noteo,
                                                       self.update,
                                                       self.config['pollInterval']
                                                       )
        self.noteo.add_event_to_queue(self.update_event)

    def get_current_song(self):
        return commands.getoutput("xmms2 current")

    def update(self):
        self.last_song = self.current_song
        self.current_song = self.get_current_song()
        if self.current_song != self.last_song:
            notification = NotificationEvent(self.noteo,
                                             0,
                                             "Now playing",
                                             self.current_song,
                                             'audio-x-generic'
                                             )
            self.noteo.add_event_to_queue(notification)
        return True

module = Xmms2
