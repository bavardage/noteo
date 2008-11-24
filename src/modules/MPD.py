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
        self.currentsong = self.lastsong = None
        try:
            self.client.connect(self.config['host'], self.config['port'])
            self.currentsong = self.lastsong = self.client.currentsong()
        except:
            self.noteo.logger.error("Couldn't connect to mpd on %s:%s" % 
                             (self.config['host'], self.config['port']))
        self.update_event = RecurringFunctionCallEvent(self.noteo, 
                                                       self.update, 
                                                       self.config['pollInterval']
                                                       )
        self.noteo.add_event_to_queue(self.update_event)

    def update(self):
        try:
            self.currentsong = self.client.currentsong()
        except:
            self.noteo.logger.error("Connection to mpd was lost")
            self.reconnect_event = RecurringFunctionCallEvent(self.noteo,
                                                              self.reconnect,
                                                              self.config['timeBetweenReconnectionAttempts'],
                                                              )
            self.noteo.add_event_to_queue(self.reconnect_event)
            return False
        if self.currentsong != self.lastsong:
            summary = 'Track changed'
            content = '\n'.join([self.currentsong[key] for key in ('title', 'artist', 'album') if key in self.currentsong])
            notification = NotificationEvent(self.noteo, 0, summary, content, "audio-x-generic")
            self.noteo.add_event_to_queue(notification)
            self.lastsong = self.currentsong
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
            self.noteo.add_event_to_queue(self.update_event)
            return False
        except:
            return True #try again

module = MPD
