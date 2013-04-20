import gtk
import re
import threading

from Noteo import *

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
        self._lock = threading.RLock()
        self.noteo.gtk_required()
        self._popups_ids = {}
        self._popups = []

    def _popup_fade_event(self, window, timeout):
            if timeout <= 0:
                timeout = self.config['defaultTimeout']
            event = FunctionCallEvent(self._fade_popup,
                                      window)
            event.delay = 3 * timeout / 4
            event.recurring_delay = timeout / 400 # TODO: option for number of steps
            self.noteo.add_event(event)
            return event.event_id

    def _popup_destroy_event(self, event_id, timeout):
            if timeout <= 0:
                timeout = self.config['defaultTimeout']
            event = FunctionCallEvent(self.noteo.invalidate_event,
                                                    event_id)
            event.delay = timeout
            self.noteo.add_event(event)
            return event.event_id

    def handle_NotificationEvent(self, event):
        with self._lock:
            window = self._create_popup(event)

            destroy_event_id = self._popup_destroy_event(event.event_id, event.get_timeout())
            fade_event_id = self._popup_fade_event(window, event.get_timeout())

            self._popups_ids[event.event_id] = [window, destroy_event_id, fade_event_id]
            self._popups.append(window)
            self._arrange_notifications()

    def replace_event(self, event_id, event):
        with self._lock:
            if event_id in self._popups_ids:
                popup = self._popups_ids.pop(event_id)
                for i in range(len(self._popups)):
                    if self._popups[i] is popup[0]:
                        window = self._create_popup(event)
                        destroy_event_id = self._popup_destroy_event(event.event_id, event.get_timeout())
                        fade_event_id = self._popup_fade_event(window, event.get_timeout())
                        self._popups_ids[event.event_id] = [window, destroy_event_id, fade_event_id]
                        self._popups[i] = window
                        break
                popup[0].destroy()
                self.noteo.invalidate_event(popup[1])
                self.noteo.invalidate_event(popup[2])
                self._arrange_notifications()

    def invalidate_event(self, event_id):
        with self._lock:
            if event_id in self._popups_ids:
                popup = self._popups_ids.pop(event_id)
                self._popups = [p for p in self._popups if p is not popup[0]]
                popup[0].destroy()
                self.noteo.invalidate_event(popup[2])
                self._arrange_notifications()

    def _fade_popup(self, window):
        window.set_opacity(window.get_opacity() - 0.01)

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
        popup.connect("button_press_event", self._button_press_event, event.event_id)
        popup.set_events(gtk.gdk.BUTTON_PRESS_MASK) # ) | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)


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
            popup = self._popups[start]
            _, y = popup.get_position()
            _, h = popup.get_size()
            y = y + (add_height * h)

        for n in range(start, len(self._popups)):
            popup = self._popups[n]
            w, h = popup.get_size()
            popup.move(x + (add_width * w),
                       y + (add_height * h))
            y = y + (height_sign * (h + v_spacing))



module = Popup
