#!/usr/bin/env python

import dbus
import dbus.service
import dbus.mainloop.glib
import gtk, gobject, gtk.gdk
import time
import sys

from Noteo import *

class Notify(NoteoModule):
    last_id = 0
    config_spec = {
        'defaultTimeout': 'float(default=7.0)',
        }
    def init(self):
        self.noteo.gtk_required()
        self._notifications = {}
        self.notification_daemon = NotificationDaemon(
            self,
            session_bus, 
            '/org/freedesktop/Notifications'
            )

    def get_id(self):
        self.last_id += 1
        return self.last_id

    def notification_received(self, id=None, **kwargs):
        if kwargs['replaces_id']:
            return self.replace_notification(**kwargs)
        else:
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
            notification = NotificationEvent(
                self.noteo,
                0,
                kwargs['summary'],
                kwargs['content'],
                icon,
                timeout,
                handled=self.popup_destroyed
                )
            self._notifications[notification] = (id if id is not None else self.get_id())
            notification.add_to_queue()
            return self._notifications[notification]

    def replace_notification(self, **kwargs):
        found = None
        for k,i in self._notifications.items():
            if i == kwargs['replaces_id']:
                found = k
        if found is not None:
            self.noteo.invalidate_event(found)
        del self._notifications[found]
        ri = kwargs['replaces_id']
        kwargs['replaces_id'] = 0
        return self.notification_received(id=ri, **kwargs)
    
    def popup_destroyed(self, event, handlers=None):
        if event in self._notifications:
            i = self._notifications[event]
            self.notification_daemon.NotificationClosed(i, 4)
            del self._notifications[event]
            #4 is undefined reason for closure
            #TODO: Do better

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
        return self.notify.notification_received(
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
