import mpd

from Noteo import *

class MPD(NoteoModule):
    config_spec = { 
        'host': 'string(default=localhost)',
        'port': 'integer(default=6600)',
        'pollInterval': 'float(default=2.5)',
        'timeBetweenReconnectionAttempts': 'integer(default=30)',
        'showFor': 'integer(default=5)',
        }
    def init(self):
        self.client = mpd.MPDClient()
        self.lastsong = None
        self.playing = None
        self._event_id = None
        self._notification_id = None
        try:
            self.client.connect(self.config['host'], self.config['port'])
            self.lastsong = self.client.currentsong()
            self.playing = self.client.status()['state'] == 'play'
        except:
            self.noteo.logger.error("Couldn't connect to mpd on %s:%s" % 
                             (self.config['host'], self.config['port']))
        event = FunctionCallEvent(self.update)
        event.recurring_delay = self.config['pollInterval']
        self._update_recurring_event(event)

        #notify_current_song_menu_item = CreateMenuItemEvent(self.noteo,
        #                                                    "Show current song",
        #                                                    self.notify_current_song,
        #                                                    icon='audio-x-generic'
        #                                                    )
        #notify_current_song_menu_item.add_to_queue()

    def _update_notification(self, notification):
        if self._notification_id is not None:
            self.noteo.replace_event(self._notification_id, notification)
        else:
            self.noteo.add_event(notification)
        self._notification_id = notification.event_id

    def _update_recurring_event(self, event):
        if self._event_id is not None:
            self.noteo.invalidate_event(self._event_id)
        self.noteo.add_event(event)
        self._event_id = event

    def notify_current_song(self, song):
        summary = '<b>Playing</b>'
        content = '\n'.join([song[key] for key in ('title', 'artist', 'album') if key in song])
        self._update_notification(NotificationEvent(summary, content, "audio-x-generic"))

    def notify_stop(self):
        summary = '<b>Paused playback</b>'
        content = ''
        self._update_notification(NotificationEvent(summary, content, "audio-x-generic"))

    def update(self):
        try:
            currentsong = self.client.currentsong()
            playing = (self.client.status()['state'] == 'play')
        except:
            self.noteo.logger.error("Connection to mpd was lost")
            event = FunctionCallEvent(self.reconnect)
            event.recurring_delay = self.config['timeBetweenReconnectionAttempts']
            self._update_recurring_event(event)
            return False
        if self.playing != playing:
            if playing:
                self.notify_current_song(currentsong)
            else:
                self.notify_stop()
        elif currentsong != self.lastsong:
            self.notify_current_song(currentsong)
        self.lastsong = currentsong
        self.playing = playing
        return True

    def reconnect(self):
        try:
            self.client.disconnect() #make sure actually disconnected
        except:
            pass
        try:
            self.client.connect(self.config['host'], self.config['port'])
            self.noteo.debug("Reconnected to MPD")
            event = FunctionCallEvent(self.update)
            event.recurring_delay = self.config['pollInterval']
            self._update_recurring_event(event)
            return False
        except:
            return True #try again

module = MPD
