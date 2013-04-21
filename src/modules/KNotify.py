import dbus

from Noteo import *

class KNotify(NoteoModule):
    config_spec = {'defaultTimeout': 'float(default=5)'}
    def init(self):
        try:
            kdehome = os.environ['KDEHOME']
        except:
            kdehome = os.path.join(os.path.expanduser("~"), ".kde")
        notifyrcPath = os.path.join(kdehome, "share/config/noteo.notifyrc")
        if os.path.isfile(notifyrcPath):
            self.write_knotifyrc(notifyrcPath)
        self.bus = dbus.SessionBus()
        self.knotify_bus = self.bus.get_object("org.kde.knotify", "/Notify")


    def do_handle_NotificationEvent(self, event):
        timeout = self.config['defaultTimeout']
        if event.get_timeout() > 0:
            timeout = event.get_timeout()
        summary = event.get_summary()
        content = event.get_content()
        content = content.replace("\n","<br>")
        self.knotify_bus.event("popup", "noteo", [],
                               '<b>' + summary + '</b> : ' + content,
                               [0,0,0,0],
                               [],
                               0,
                               dbus_interface="org.kde.KNotify")

    def write_knotifyrc(self, path):
        with open(path,"w") as f:
            f.write("[Event/popup]\nAction=Popup|Taskbar\nExecute=\nKTTS=\nLogfile=\nSound=")

module = KNotify
