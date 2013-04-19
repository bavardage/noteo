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
        self._popup = None
        try:
            self.client.connect(self.config['host'], self.config['port'])
            self.lastsong = self.client.currentsong()
            self.playing = self.client.status()['state'] == 'play'
        except:
            self.noteo.logger.error("Couldn't connect to mpd on %s:%s" % 
                             (self.config['host'], self.config['port']))
        self.update_event = RecurringFunctionCallEvent(self.noteo, 
                                                       self.update, 
                                                       self.config['pollInterval']
                                                       )
        self.update_event.add_to_queue()
        notify_current_song_menu_item = CreateMenuItemEvent(self.noteo,
                                                            "Show current song",
                                                            self.notify_current_song,
                                                            icon='audio-x-generic'
                                                            )
        notify_current_song_menu_item.add_to_queue()

    def notify_current_song(self, song):
        if self._popup is not None:
            self.noteo.invalidate_to_modules(self._popup)
        summary = '<b>Playing</b>'
        content = '\n'.join([song[key] for key in ('title', 'artist', 'album') if key in song])

        notification = NotificationEvent(self.noteo, 0, summary, content, "audio-x-generic")
        self._popup = notification
        notification.add_to_queue()

    def notify_stop(self):
        if self._popup is not None:
            self.noteo.invalidate_to_modules(self._popup)
        summary = '<b>Paused playback</b>'
        content = ''
        notification = NotificationEvent(self.noteo, 0, summary, content, "audio-x-generic")
        self._popup = notification
        notification.add_to_queue()

    def update(self):
        try:
            currentsong = self.client.currentsong()
            playing = (self.client.status()['state'] == 'play')
        except:
            self.noteo.logger.error("Connection to mpd was lost")
            self.reconnect_event = RecurringFunctionCallEvent(self.noteo,
                                                              self.reconnect,
                                                              self.config['timeBetweenReconnectionAttempts'],
                                                              )
            self.reconnect_event.add_to_queue()
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
            self.update_event = RecurringFunctionCallEvent(self.noteo, self.upate, self.config['pollInterval'])
            self.update_event.add_to_queue()
            return False
        except:
            return True #try again

module = MPD
