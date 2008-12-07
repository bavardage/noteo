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
        notify_current_song_menu_item = CreateMenuItemEvent(self.noteo,
                                                            "Show current song",
                                                            self.notify_current_song,
                                                            icon='audio-x-generic'
                                                            )
        self.noteo.add_event_to_queue(notify_current_song_menu_item)

    def get_current_song(self):
        return commands.getoutput("xmms2 current")

    def notify_current_song(self):
        notification = NotificationEvent(self.noteo,
                                             0,
                                             "Now playing",
                                             self.current_song,
                                             'audio-x-generic'
                                             )
        self.noteo.add_event_to_queue(notification)

    def update(self):
        self.last_song = self.current_song
        self.current_song = self.get_current_song()
        if self.current_song != self.last_song:
            self.notify_current_song()
        return True

module = Xmms2
