#!/usr/bin/env python

import dbus
import dbus.service
import dbus.mainloop.glib
import gtk, gobject, gtk.gdk
import time
import sys

from Noteo import *

class Notify(NoteoModule):
    config_spec = {
        'defaultTimeout': 'float(default=7.0)',
        }
    def init(self):
        self.noteo.gtk_required()

        self._last_id = 0
        self._lock = threading.RLock()

        self._event_id = {}
        self._notification_id = {}

        self.notification_daemon = NotificationDaemon(
            self,
            session_bus, 
            '/org/freedesktop/Notifications'
            )

    def _notification_received(self, id=None, **kwargs):
        with self._lock:
            if id is not None and \
               id in self._event_id:
                self.noteo.logger.error("Received duplicate id")
                return None

            if kwargs['expire'] == -1:
                timeout = self.config['defaultTimeout']
            else:
                timeout = kwargs['expire']/1000 #convert from millis to secs

            if 'icon_data' in kwargs['hints']:
                icon_data = kwargs['hints']['icon_data']
                (width, height, rowstride, has_alpha,
                 bps, channels, data) = icon_data
                try:
                    data = "".join(data)
                    icon = gtk.gdk.pixbuf_new_from_data(
                        data, 
                        gtk.gdk.COLORSPACE_RGB, 
                        has_alpha, 
                        bps, 
                        width, 
                        height, 
                        rowstride
                        )
                except:
                    icon = kwargs['icon']
                    self.noteo.logger.error(
                        "Error creating pixbuf %s" % ",".join(sys.exc_info())
                        )
            else:
                icon = kwargs['icon']

            notification = NotificationEvent(kwargs['summary'], kwargs['content'], icon, timeout)

            if kwargs['replaces_id']:
                self._replace_notification(kwargs['replaces_id'], notification)
            else:
                self.noteo.add_event(notification)

            if id is None:
                id = self._get_uid()
            self._event_id[id] = notification.event_id
            self._notification_id[notification.event_id] = id
            return id

    def _replace_notification(self, id, notification):
        if id in self._event_id:
            event_id = self._event_id.pop(id)
            del self._notification_id[event_id]
            self.noteo.replace_event(event_id, notification)
        else:
            self.noteo.add_event(notification)

    def invalidate_event(self, event_id):
        with self._lock:
            if event_id in self._notification_id:
                i = self._notification_id[event_id]
                self.notification_daemon.NotificationClosed(i, 4)
                id = self._notification_id.pop(event_id)
                del self._event_id[id]
                #4 is undefined reason for closure

    def _get_uid(self):
        with self._lock:
            self._last_id += 1
            return self._last_id

class NotificationDaemon(dbus.service.Object):

    def __init__(self, notify, bus, name):
        self.notify = notify
        super(NotificationDaemon, self).__init__(bus, name)
    
    def set_session_bus(self, session_bus):
        self.session_bus = session_bus

    @dbus.service.method("org.freedesktop.Notifications", 
                         in_signature='susssasa{ss}i',
                         out_signature='u',
                         byte_arrays=True)
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        return self.notify._notification_received(
            app_name=app_name,
            replaces_id=replaces_id,
            icon=app_icon,
            summary=summary,
            content=body,
            actions=actions,
            hints=hints,
            expire=expire_timeout
            )

    @dbus.service.method("org.freedesktop.Notifications",
                         in_signature='', out_signature='as')
    def GetCapabilities(self):
        return ("body", "body-markup")

    @dbus.service.method("org.freedesktop.Notifications",
                         in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ("Notification Daemon", "Noteo", "0", "0")
    
    @dbus.service.signal("org.freedesktop.Notifications",
                         signature='uu')
    def NotificationClosed(self, id_in, reason_in):
        pass

        
    @dbus.service.method("org.freedesktop.Notifications", in_signature='u', out_signature='')
    def CloseNotification(self, id):
        print "Close it omg"

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
session_bus = dbus.SessionBus()
name = dbus.service.BusName("org.freedesktop.Notifications", session_bus)
#object = NotificationDaemon(session_bus, '/org/freedesktop/Notifications')

module=Notify
