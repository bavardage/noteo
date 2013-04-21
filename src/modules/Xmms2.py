import commands

from Noteo import *

class Xmms2(NoteoModule):
    config_spec = {'pollInterval': 'float(default=2.0)'}
    def init(self):
        self.current_song = self.get_current_song()
        update_event = FunctionCallEvent(self.update)
        update_event.recurring_delay = self.config['pollInterval']
        self.noteo.add_event(update_event)

        self.noteo.add_event(CreateMenuItemEvent("Show current song",
                                                 self.notify_current_song,
                                                 icon='audio-x-generic'))

    def get_current_song(self):
        return commands.getoutput("xmms2 current")

    def notify_current_song(self):
        self.noteo.add_event(NotificationEvent("Now playing",
                                               self.current_song,
                                               'audio-x-generic'))

    def update(self):
        self.last_song = self.current_song
        self.current_song = self.get_current_song()
        if self.current_song != self.last_song:
            self.notify_current_song()
        return True

module = Xmms2
