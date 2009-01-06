import gtk

from Noteo import *

class DesktopDisplay(NoteoModule):
    config_spec = {
        'xOffset': 'integer(default=30)',
        'yOffset': 'integer(default=30)',
        'opacity': 'float(default=0.5)',
        'maxCharsPerLine': 'integer(default=20)',
        'showIcons': 'boolean(default=True)',
        'height': 'integer(default=400)',
        }
    def init(self):
        self.noteo.gtk_required()
        self.init_gui()
        self.position_window()

    def init_gui(self):
        self.window = gtk.Window()
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
        self.window.set_opacity(self.config['opacity'])
        
        self.scrolled = scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        
        self.vbox = gtk.VBox(False)

        scrolled.add_with_viewport(self.vbox)
        
        self.window.add(scrolled)
        self.window.show_all()

    def position_window(self):
        self.window.resize(300, self.config['height'])
        x,y = (self.config['xOffset'], self.config['yOffset'])
        self.window.move(x, y)
            
    def do_handle_NotificationEvent(self, event):
        summary = event.get_summary()
        message = event.get_content()
        icon = event.get_icon()

        label = gtk.Label(summary + "\n" + message)
        label.set_line_wrap(True)
        label.set_width_chars(self.config['maxCharsPerLine'])
        if icon and self.config['showIcons']:
            hbox = gtk.HBox()
            hbox.pack_start(gtk.image_new_from_pixbuf(icon))
            hbox.pack_start(label)
            self.vbox.pack_start(hbox)
        else:
            self.vbox.pack_start(label)
        self.vbox.pack_start(gtk.HSeparator())
        self.vbox.show_all()

        #scroll to bottom
        adjustment = self.scrolled.get_vadjustment()
        adjustment.set_value(adjustment.upper)
        
module = DesktopDisplay
