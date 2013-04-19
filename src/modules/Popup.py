import gtk
import re

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
        self.noteo.gtk_required()
        self._popups = {}

    def handle_NotificationEvent(self, event):
        self._popups[event] = self.create_popup(event)
        popup_timeout = self.config['defaultTimeout']
        if event.get_timeout() > 0:
            popup_timeout = event.get_timeout()
        destroy_popup_event = FunctionCallEvent(
            self.noteo,
            popup_timeout,
            self.popup_expired_for_event,
            event)
        destroy_popup_event.add_to_queue()
        self.position_popup_for_event(event)
        
    def event_is_invalid(self, event):
        self.destroy_popup_for_event(event)

    def popup_expired_for_event(self, event):
        self.destroy_popup_for_event(event)
        event.handled(event)

    def button_press_event(self, window, gdk_event,  event):
        self.noteo.invalidate_to_modules(event)

    def create_popup(self, event):
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
        popup.connect("button_press_event", self.button_press_event, event)
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

    def destroy_popup_for_event(self, event):
        sign = 1 if self.config['verticalArrangement'] == 'ascending' else -1
        if event in self._popups:
            popup = self._popups.pop(event)
            w, h = popup.get_size()
            popup.destroy()
            for e,p in self._popups.items():
                if e > event:
                    x, y = p.get_position()
                    p.move(x, y + (sign * h))
            return True
        else:
            return False

    def position_popup_for_event(self, event):
        vertical_arrangement = self.config['verticalArrangement']
        horizontal_arrangement = self.config['horizontalArrangement']
        xoffset = self.config['xOffset']
        yoffset = self.config['yOffset']
        vertical_spacing = self.config['verticalSpacing']
        width, height = self._popups[event].get_size()
        self.noteo.logger.debug("Positioning window of size (%s, %s)" % (width, height))
        popup_x, popup_y = xoffset, 0
        if vertical_arrangement == 'descending':
            greatest_height = yoffset - vertical_spacing
            for e, p in self._popups.items():
                w,h = p.get_size()
                x, y = p.get_position()
                if (e is not event) and y + h > greatest_height:
                    greatest_height = y + h
            popup_y = greatest_height + vertical_spacing
        else:
            smallest_height = gtk.gdk.screen_height() - yoffset + vertical_spacing
            for e,p in self._popups.items():
                x, y = p.get_position()
                if (e is not event) and y < smallest_height:
                    smallest_height = y
            popup_y = smallest_height - height - vertical_spacing
        if horizontal_arrangement == 'right':
            popup_x = gtk.gdk.screen_width() - width - xoffset
        self._popups[event].show_all()
	self._popups[event].move(popup_x, popup_y)
        self.noteo.gtk_update()
               
            

module = Popup
