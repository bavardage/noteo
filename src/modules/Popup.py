import gtk

from Noteo import *

class Popup(NoteoModule):
    def init(self):
        self._popups = {}
        self.config = {'defaultTimeout': 5,}

    def handle_event(self, event):
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
        self.noteo.add_event_to_queue(destroy_popup_event)
        self.position_popup_for_event(event)
        
    def event_is_invalid(self, event):
        self.destroy_popup_for_event(event)

    def popup_expired_for_event(self, event):
        self.destroy_popup_for_event(event)
        event.handled()

    def create_popup(self, summary, content, icon):
        popup = gtk.Window(gtk.WINDOW_POPUP)
        
        summary_label = gtk.Label(summary)
        content_label = gtk.Label(content)

        vbox = gtk.VBox()
        vbox.pack_start(summary_label)
        vbox.pack_start(content_label)

        popup.add(vbox)
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
        vertical_arrangement = 'desocending'
        horizontal_arrangement = 'right'
        width, height = self._popups[event].get_size()
        popup_y, popup_x = 0,0
        if vertical_arrangement == 'descending':
            greatest_height = 0
            for e, p in self._popups.items():
                w,h = p.get_size()
                x, y = p.get_position()
                if (e is not event) and y + h > greatest_height:
                    greatest_height = y + h
            popup_y = greatest_height
        else:
            smallest_height = gtk.gdk.screen_height()
            for e,p in self._popups.items():
                x, y = p.get_position()
                print y, smallest_height
                if (e is not event) and y < smallest_height:
                    smallest_height = y
            popup_y = smallest_height - height
        if horizontal_arrangement == 'right':
            popup_x = gtk.gdk.screen_width() - width
        self._popups[event].move(popup_x, popup_y)
        self.noteo.gtk_update()
               
            

module = Popup
