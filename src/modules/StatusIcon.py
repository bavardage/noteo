import gtk
import sys

from Noteo import *

class StatusIcon(NoteoModule):
    def init(self):
        #tell noteo we are using gtk
        self.noteo.gtk_required()
        #setup status icon
        self.status_icon = gtk.StatusIcon()
        self.status_icon.set_from_file('/usr/share/pixmaps/noteo.png')
        self.status_icon.connect('popup_menu', self.show_menu)
        #basic menu items
        self.menu = gtk.Menu()
        quit = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
        quit.connect("activate", self.quit)
        self.menu.append(gtk.SeparatorMenuItem())
        self.menu.append(quit)
        self.menu.show_all()
        
    def show_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    def call_callback(self, menuitem, callback):
        callback()

    def do_handle_CreateMenuItemEvent(self, event):
        icon = event.get_icon(32)
        if icon is None:
            item = gtk.MenuItem(label=event.label)
        else:
            item = gtk.ImageMenuItem(event.label)
            image = gtk.image_new_from_pixbuf(icon)
            item.set_image(image)
        item.connect("activate", self.call_callback, event.callback)
        self.menu.prepend(item)
        self.menu.show_all()

    def quit(self, *args):
        quit_event = QuitEvent(self.noteo, 1) #quit in one second
        quit_event.add_to_queue()
    
module = StatusIcon
