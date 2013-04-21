import gtk
import re
import threading

from Noteo import *

class PopupItem(object):
    def __init__(self, noteo, event_id, window, timeout):
        self.event_id = event_id
        self.noteo = noteo
        self.window = window
        self.timeout = timeout
        self._fade_event = None
        self._destroy_event = None

    def add_events(self):
        self.invalidate_events()
        self._fade_event = self._create_fade_event(self.window, self.timeout)
        self._destroy_event = self._create_destroy_event(self.event_id, self.timeout)

    def invalidate_events(self):
        if self._destroy_event is not None:
            self.noteo.invalidate_event(self._destroy_event)
            self._destroy_event = None

        if self._fade_event is not None:
            self.noteo.invalidate_event(self._fade_event)
            self._fade_event = None

    def destroy(self):
        self.window.destroy()
        self.invalidate_events()

    def _fade_popup(self):
        if self._fade_event is not None:
            print "opacity down",threading.current_thread()
            self.window.set_opacity(self.window.get_opacity() - 0.01)

    def _create_fade_event(self, window, timeout):
        event = FunctionCallEvent(self._fade_popup)
        event.delay = 3 * timeout / 4
        event.recurring_delay = timeout / 400 # TODO: option for number of steps
        self.noteo.add_event(event)
        return event.event_id

    def _create_destroy_event(self, event_id, timeout):
        if timeout <= 0:
            timeout = self.config['defaultTimeout']
        event = FunctionCallEvent(self.noteo.invalidate_event,
                                                event_id)
        event.delay = timeout
        self.noteo.add_event(event)
        return event.event_id

class Popup(NoteoModule):
    config_spec = {
        'defaultTimeout': 'float(default=5)',
        'verticalArrangement': 'string(default=\'ascending\')',
        'horizontalArrangement': 'string(default=\'right\')',
        'opacity': 'float(default=0.8)',
        'maxCharsPerLine': 'integer(default=30)',
        'xOffset': 'integer(default=0)',
        'yOffset': 'integer(default=30)',
        'verticalSpacing': 'integer(default=2)',
        'use-custom-colours': 'boolean(default=False)',
        'fg-colour': 'string(default=\'#ffffff\')',
        'bg-colour': 'string(default=\'#131313\')',
        }

    def init(self):
        self.noteo.gtk_required()
        self._popups = {}
        self._popup_queue = []

    def _get_timeout(self, timeout):
        if timeout <= 0:
            return self.config['defaultTimeout']
        return timeout

    def handle_NotificationEvent(self, event):
        event_id = event.event_id

        item =  PopupItem(self.noteo,
                          event_id,
                          self._create_popup(event),
                          self._get_timeout(event.get_timeout()))

        self._popups[event_id] = item
        self._popup_queue.append(event_id)
        self._arrange_notifications()
        item.add_events()

    def replace_event(self, event_id, event):
        if event_id not in self._popups:
            return False
        popup = self._popups.pop(event_id)
        popup.destroy()
        i = self._popup_queue.index(event_id)
        item =  PopupItem(self.noteo,
                          event.event_id,
                          self._create_popup(event),
                          self._get_timeout(event.get_timeout()))

        self._popups[event.event_id] = item
        self._popup_queue[i] = event.event_id
        print (self._popup_queue, self._popups.keys())
        item.add_events()
        self._arrange_notifications()

    def invalidate_event(self, event_id):
        if event_id not in self._popups:
            return False
        popup = self._popups.pop(event_id)
        self._popup_queue = [id for id in self._popup_queue if id != event_id]
        popup.destroy()
        self._arrange_notifications()

    def _leave_notify_event(self, window, gdk_event, event_id):
        item = self._popups[event_id]
        item.invalidate_events()
        window.set_opacity(self.config['opacity'])
        item.add_events()

    def _enter_notify_event(self, window, gdk_event, event_id):
        item = self._popups[event_id]
        item.invalidate_events()
        print "opacity 1", threading.current_thread()
        window.set_opacity(1)#self.config['opacity'])

    def _motion_notify_event(self, window, gdk_event, event_id):
        print "opacity 1", threading.current_thread()
#        window.set_opacity(1)#self.config['opacity'])

    def _button_press_event(self, window, gdk_event,  event_id):
        self.noteo.invalidate_event(event_id)

    def _create_popup(self, event):
        summary = event.get_summary()
        content = event.get_content()
        icon = event.get_icon()

        replace_amp = re.compile(u'&(?![a-zA-Z]{1,8};)')

        while re.findall(replace_amp, summary):
            summary = re.sub(replace_amp, "&amp;", summary)

        while re.findall(replace_amp, content):
            content = re.sub(replace_amp, "&amp;", content)

        popup = gtk.Window(gtk.WINDOW_POPUP)
        max_chars = self.config['maxCharsPerLine']
        popup.set_opacity(self.config['opacity'])
        # Event signals
#        popup.connect("motion_notify_event", self._motion_notify_event, event.event_id)
        popup.connect("enter_notify_event", self._enter_notify_event, event.event_id)
        popup.connect("leave_notify_event", self._leave_notify_event, event.event_id)
        popup.connect("button_press_event", self._button_press_event, event.event_id)
        popup.set_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.ENTER_NOTIFY_MASK | gtk.gdk.LEAVE_NOTIFY_MASK)# | gtk.gdk.MOTION_NOTIFY)


        vbox = gtk.VBox()
        for item in (summary, content):
            label = gtk.Label()
            label.set_justify(gtk.JUSTIFY_CENTER)
            label.set_markup(item)
            label.set_line_wrap(True)
            label.set_width_chars(max_chars)
            label.show()
            if self.config['use-custom-colours']:
                label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.config['fg-colour']))
            vbox.pack_start(label)

        hbox = gtk.HBox()
        hbox.pack_start(gtk.image_new_from_pixbuf(icon))
        hbox.pack_start(vbox)

        if self.config['use-custom-colours']:
            popup.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.config['bg-colour']))

        popup.add(hbox)
        popup.show_all()

        return popup


    def _base_position(self):
        v_arrange = self.config['verticalArrangement']
        h_arrange = self.config['horizontalArrangement']
        x_offset = self.config['xOffset']
        y_offset = self.config['yOffset']
        if v_arrange == 'TB':
            y = y_offset
        elif v_arrange == 'BT':
            y = gtk.gdk.screen_height() - y_offset
        else:
            raise ValueError("vertical_arrangement must either be TB or BT")
        if h_arrange == 'LR':
            x = x_offset
        elif h_arrange == 'RL':
            x = gtk.gdk.screen_width() - x_offset
        else:
            raise ValueError("horizontalArrangement must either be LR or RL")
        return (x, y)


    def _arrange_notifications(self, start = 0):
        height_sign = 1 if self.config['verticalArrangement'] == 'TB' else -1
        add_height = 0 if self.config['verticalArrangement'] == 'TB' else -1
        add_width = 1 if self.config['horizontalArrangement'] == 'LR' else -1
        v_spacing = self.config['verticalSpacing']

        x, y = self._base_position()
        if start:
            window = self._popups[self._popup_queue[start]].window
            _, y = window.get_position()
            _, h = window.get_size()
            y = y + (add_height * h)

        for n in range(start, len(self._popup_queue)):
            window = self._popups[self._popup_queue[n]].window
            w, h = window.get_size()
            window.move(x + (add_width * w),
                       y + (add_height * h))
            y = y + (height_sign * (h + v_spacing))



module = Popup
