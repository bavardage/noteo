import gtk

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
        }
    def init(self):
        self.noteo.gtk_required()
        self._popups = {}

    def handle_NotificationEvent(self, event):
        self._popups[event] = self.create_popup(
            event.get_summary(),
            event.get_content(),
            event.get_icon()
            )
        popup_timeout = 5
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

    def create_popup(self, summary, content, icon):

        summary = summary.replace('&', '&amp;')
        content = content.replace('&', '&amp;')

        popup = gtk.Window(gtk.WINDOW_POPUP)
        max_chars = self.config['maxCharsPerLine']
        
        summary_label = gtk.Label()
        summary_label.set_markup(summary)
        summary_label.show()
        summary_label.set_line_wrap(True)
        summary_label.set_width_chars(max_chars)
        
        content_label = gtk.Label()
        content_label.set_markup(content)
        content_label.show()
        content_label.set_line_wrap(True)
        content_label.set_width_chars(max_chars)

        vbox = gtk.VBox()
        
        vbox.pack_start(summary_label)
        vbox.pack_start(content_label)

        hbox = gtk.HBox()
        hbox.pack_start(gtk.image_new_from_pixbuf(icon))
        hbox.pack_start(vbox)
        
        popup.add(hbox)
        popup.set_opacity(self.config['opacity'])
        popup.show_all()
        

        return popup

    def destroy_popup_for_event(self, event):
        if event in self._popups:
            popup = self._popups.pop(event)
            popup.destroy()
            return True
        else:
            return False

    def position_popup_for_event(self, event):
        vertical_arrangement = self.config['verticalArrangement']
        horizontal_arrangement = self.config['horizontalArrangement']
        xoffset = self.config['xOffset']
        yoffset = self.config['yOffset']
        width, height = self._popups[event].get_size()
        self.noteo.logger.debug("Positioning window of size (%s, %s)" % (width, height))
        popup_x, popup_y = xoffset, 0
        if vertical_arrangement == 'descending':
            greatest_height = yoffset
            for e, p in self._popups.items():
                w,h = p.get_size()
                x, y = p.get_position()
                if (e is not event) and y + h > greatest_height:
                    greatest_height = y + h
            popup_y = greatest_height
        else:
            smallest_height = gtk.gdk.screen_height() - yoffset
            for e,p in self._popups.items():
                x, y = p.get_position()
                if (e is not event) and y < smallest_height:
                    smallest_height = y
            popup_y = smallest_height - height
        if horizontal_arrangement == 'right':
            popup_x = gtk.gdk.screen_width() - width - xoffset
        self._popups[event].move(popup_x, popup_y)
        self.noteo.gtk_update()
               
            

module = Popup
