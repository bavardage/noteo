#!/usr/bin/env python

import dbus
import dbus.service
import dbus.mainloop.glib
import gtk, gobject
import time

from Noteo import *

class Notify(NoteoModule):
    last_id = 0
    def init(self):
        self.config = {'pollInterval': 1, 'defaultTimeout': 5}
        self._notifications = {}
        self.notification_daemon = NotificationDaemon(
            self,
            session_bus, 
            '/org/freedesktop/Notifications'
            )
        self.collect_notifications_event = \
            RecurringFunctionCallEvent(
            self.noteo, 
            self.noteo.gtk_update, 
            self.config['pollInterval']
            )
        self.noteo.add_event_to_queue(self.collect_notifications_event)

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
            notification = NotificationEvent(
                self.noteo,
                0,
                kwargs['summary'],
                kwargs['content'],
                kwargs['icon'],
                timeout,
                handled=self.popup_destroyed
                )
            self._notifications[notification] = (id if id is not None else self.get_id())
            self.noteo.add_event_to_queue(notification)
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
                             out_signature='u')
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

print object

module=Notify
