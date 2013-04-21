#!/usr/bin/env python
# Noteo v 0.1.0
# Copyright Ben Duffield 2008
# Released under the GPL
'''
    Noteo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Foobar is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
'''
import heapq
import time
import logging
import os
import sys
import threading
import uuid
try:
    import glib
    import gtk
    NO_GTK = False
except:
    print "Warning: No gtk support. "
    print "Don't be surprised when your gtk-wanting modules go \"oh noes\""
    NO_GTK = True

try:
    from PyQt4 import QtGui, QtCore
    NO_PYQT = False
except:
    print "Warning: No QT4 support."
    print "Don't be surprised when your gtk-hating modules go \"you fail\""
    NO_PYQT = True

from configobj import ConfigObj
from validate import Validator

class NoteoConfig:
    def __init__(self, filename, configspec):
        self.config = ConfigObj(filename, configspec=configspec)
        self.config.validate(Validator(), copy=True)
        self.config.write() #write default values

    def __getitem__(self, field):
        try:
            return self.config[field]
        except(KeyError):
            raise KeyError, field + " is not a valid config option"

def get_icon(icon, size=64):
    '''get_icon(size=64)
    uses the value of self.icon
    if self.icon is an icon, then this is simply returned
    if icon is a path to an image, this image is loaded and returned,
    if icon is a string, this is looked up as a gtk icon
    returns a gtk.gdk.Pixbuf if an icon can be found, or None otherwise'''
    if NO_GTK:
        return None
    elif icon is None:
        return None
    elif isinstance(icon, gtk.gdk.Pixbuf):
        return icon
    elif os.path.exists(icon):
        return gtk.gdk.pixbuf_new_from_file_at_size(icon, size, size)
    else:
        icon_theme = gtk.icon_theme_get_default()
        if icon_theme.has_icon(icon):
            try:
                return icon_theme.load_icon(icon, size, 0)
            except:
                return None
        return None

class Event(object):
    def __init__(self, event_id=None):
        if event_id is None:
            event_id = uuid.uuid4()
        self._event_id = event_id
        self._callback = None
        self.recurring_delay = -1
        self.delay = 0

    def set_callback(self, fun, *args, **kargs):
        self._callback = [fun, args, kargs]


    @property
    def event_id(self):
        return self._event_id

    def handled(self):
        if self._callback is not None:
            self._callback[0](self, *self._callback[1], **self._callback[2])

    #comparison
    def __lt__(self, other):
        return self.event_id < other.event_id
    def __le__(self, other):
        return self.event_id <= other.event_id
    def __eq__(self, other):
        return self.event_id == other.event_id
    def __ne__(self, other):
        return self.event_id != other.event_id
    def __gt__(self, other):
        return self.event_id > other.event_id
    def __ge__(self, other):
        return self.event_id >= other.event_id
    #representations
    def __repr__(self):
        return "%s %s" % (self.__class__.__name__, self.event_id)

class NotificationEvent(Event):
    def __init__(self, summary, content, icon="", timeout=-1, *args, **kargs):
        self._summary = summary
        self._content = content
        self._icon = icon
        self._timeout = timeout
        super(NotificationEvent, self).__init__(*args, **kargs)

    def __repr__(self):
        return '"%s" "%s" "%s"' % (self._summary, self._content, self._icon)

    def get_summary(self):
        return str(self._summary)

    def get_content(self):
        return str(self._content)

    def get_icon(self, size=64):
        return get_icon(self._icon, size)

    def get_timeout(self):
        return self._timeout


class HandleableEvent(Event):
    def __init__(self, *args, **kargs):
        super(HandleableEvent, self).__init__(*args, **kargs)

    def handle(self):
        raise Exception("Handle not implemented")


class FunctionCallEvent(HandleableEvent):
    def __init__(self, function, *args, **kwargs):
        self.function = function
        self.args = args
        self.kwargs = kwargs
        super(FunctionCallEvent, self).__init__()

    def handle(self):
        return_value = None
        if callable(self.function):
            return_value = self.function(*self.args, **self.kwargs)
        return return_value


class CreateMenuItemEvent(Event):
    def __init__(self, label, callback, icon=None):
        self.label = label
        self.callback = callback
        self.icon = icon
        super(CreateMenuItemEvent, self).__init__()

    def get_icon(self, size=64):
        return get_icon(self.icon, size)

class QuitEvent(Event):
    def __init__(self):
        super(QuitEvent, self).__init__()

    def handle(self):
        try:
            gtk.main_quit()
            #gotta find out how to tell QT to stfu and quit
        except:
            pass
        sys.exit(0)

class NoteoModule(object):
    '''NoteoModule is used to provide most of noteo's functionality
    This should not be used by itself, but used as a super class'''
    config_spec = {}
    def __init__(self, noteo, path=""):
        self.noteo = noteo
        self.modulename = self.__class__.__name__
        self.noteo.logger.info("Initialising module %s" % self.modulename)
        self.path = path
        self.configure()
        self.init()

    def init(self):
        '''init()
        You should overload this instead of providing an __init__ function
        By the time init() is called, everything should work properly.'''
        pass

    def configure(self):
        config_path = os.path.join(self.noteo.config_dir, self.__class__.__name__)
        self.config = NoteoConfig(config_path, self.config_spec)

    def handle_event(self, event):
        superclasses = event.__class__.mro()
        for supercls in superclasses:
            name = supercls.__name__
            if name == 'Event':
                return self.do_handle_event(event)
            elif hasattr(self, "handle_%s" % name):
                return getattr(self, "handle_%s" % name)(event)
            elif hasattr(self, "do_handle_%s" % name):
                return getattr(self, "do_handle_%s" % name)(event)
        self.noteo.logger.error("Reached end of handle_event in %s, this probably shouldn't happen" % self.modulename)
        self.noteo.logger.error("Event had type: %s, mro of (%s)" % (event.__class__.__name__, event.__class__.mro()))
        return None

    def replace_event(self, event_id, event):
        '''replace_event(event_id, event)
        overload this when you want to do something with the event.'''
        pass

    def do_handle_event(self, event_id):
        '''do_handle_event(event)
        overload this when you want to do something with the event,
        but the event is handled straight away - you will usually want to
        do this. Overload handle_event when you want more control'''
        pass

    def invalidate_event(self, event_id):
        '''invalidate_event(event_id)
        this is called when an event is made invalid before it is due to be
        called. If the event doesn't exist, then this should gracefully do 
        nothing'''
        pass

class ThreadedEventQueue:
    def __init__(self, callback, *args, **kargs):
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._queue = []
        self._callback = [callback, args, kargs]
        self._end = False

    def start_thread(self):
        with self._lock:
            while not self._end:
                if not len(self._queue):
                    self._condition.wait()
                elif self._queue[0][0] > time.time():
                    self._condition.wait(self._queue[0][0] - time.time())
                else:
                    ev = heapq.heappop(self._queue)[1]
                    self._callback[0](ev, *self._callback[1], **self._callback[2])

    def replace(self, event_id, event):
        with self._lock:
            tmp = []
            for x in self._queue:
                if event_id == x[1].event_id:
                    x[1] = event
                    break

    def remove(self, event_id):
        with self._lock:
            tmp = []
            for x in self._queue:
                if event_id != x[1].event_id:
                    heapq.heappush(tmp, x)
            self._queue = tmp

    def push(self, time, event):
        with self._lock:
            heapq.heappush(self._queue, [time, event])
            self._condition.notify()

    def __repr__(self):
        with self._lock:
            return str(self._queue)

class Noteo:
    logger = logging
    #event loop stuff
    event_loop_running = False
    event_timer = None
    #gtk
    gtk_is_required = False
    #qt
    qt_is_required = False
    #module, paths, etc
    local_module_dir = os.path.expandvars('$HOME/.noteo')
    module_dir = '/usr/share/noteo/modules/'
    config_dir = os.path.expandvars('$HOME/.config/noteo')

    def __init__(self, load_modules = True):
        self._event_queue = ThreadedEventQueue(self._handle_event)

        self._configure()
        self._modules = []
        if load_modules:
            self._load_modules()

    #configuration
    def _configure(self):
        try:
            os.makedirs(Noteo.config_dir)
        except:
            #self.logger.debug("Noteo configuration directory already exists")
            pass
        config_spec = {
            'localmodules': 'list(default=list(\'\'))',
            'modules': 'list(default=list(BatteryCheck, Dmesg, Awesome, GmailCheck, Xmms2, MPD, DirectoryWatcher, StatusIcon, Notify, Popup, PacmanCheck, DesktopDisplay))',
            'debugLevel': 'integer(default=30)', #logger.WARNING = 30 
            }
        config_path = os.path.join(Noteo.config_dir, 'Noteo')
        self.config = NoteoConfig(config_path, config_spec)
        self.logger.basicConfig(level=self.config['debugLevel'])
        print "logging initialised for debug level %s" % self.config['debugLevel']

    #modules
    def _load_modules(self):
        self.logger.info("Loading modules")
        for module_name in self.config['modules']:
            self._load_module(module_name, local=False)
        for module_name in self.config['localmodules']:
            self._load_module(module_name, local=True)

    def _load_module(self, module_name, local=False):
        if module_name == '':
            self.logger.debug('Was trying to load a module with no name - not even bothering to try')
            return
        if local:
            path = Noteo.local_module_dir
        else:
            path = Noteo.module_dir
        sys.path.append(path)
        try:
            module = __import__(module_name).module(self, path)
            self._modules.append(module)
        except:
            self.logger.error("Errors occured when importing the module %s" % module_name)
            self.logger.error("The error were: %s" % str(sys.exc_info()))
            #raise
        finally:
            sys.path.pop()

    def _handle_event(self, event):
        self.logger.debug("handling event (%s)" % event)
        if isinstance(event, HandleableEvent):
            event.handle()
        else:
            for module in self._modules:
                module.handle_event(event)
        event.handled()
        if event.recurring_delay >= 0:
            self._event_queue.push(time.time() + event.recurring_delay, event)

    def start(self):
        self._event_queue.start_thread()

    #events
    def add_event(self, event):
        self._event_queue.push(time.time() + event.delay, event)

    def invalidate_event(self, event_id):
        self.logger.debug("invalidating event (%s)" % event_id)
        self._event_queue.remove(event_id)
        self.add_event(FunctionCallEvent(self._invalidate_to_modules, event_id))

    def _invalidate_to_modules(self, event_id):
        self.logger.debug("invalidating event to modules (%s)" % event_id)
        for module in self._modules:
            module.invalidate_event(event_id)

    def replace_event(self, event_id, event):
        self.logger.debug("replacing event (%s)" % event_id)
        self._event_queue.replace(event_id, event)
        self.add_event(FunctionCallEvent(self._replace_to_modules, event_id, event))

    def _replace_to_modules(self, event_id, event):
        self.logger.debug("replacing event to modules (%s)" % event_id)
        for module in self._modules:
            module.replace_event(event_id, event)

    def gtk_required(self):
        self.logger.debug("GTK is required")
        self.logger.debug("Already required? %s" % self.gtk_is_required)
        gtk.gdk.threads_init()
        if NO_GTK:
            self.logger.warning("pygtk is not installed, therefore no gtk support")
            return
        if not self.gtk_is_required:
            self.logger.debug("Not already set-up. Setting up...")
            event = FunctionCallEvent(self.gtk_update)
            event.recurring_delay = 0.01
            self.add_event(event)
        self.gtk_is_required = True

    def gtk_update(self):
        while gtk.events_pending():
            gtk.main_iteration()
        return True

    def qt_required(self):
        self.logger.debug("QT4 is required")
        self.logger.debug("Already required? %s" % self.qt_is_required)
        if NO_PYQT:
            self.logger.warning("pyqt4 is not installed, therefore no qt support")
            return
        if not self.qt_is_required:
            self.logger.debug("Not already set-up. Setting up...")    
            self.qt_app = QtGui.QApplication(sys.argv)
            event = FunctionCallEvent(self.qt_update)
            event.recurring_delay = 0.1
            self.add_event(event)
        self.qt_is_required = True

    def qt_update(self):
        QtGui.qApp.processEvents()
        return True

def run_noteo():
    print "running noteo..."
    noteo = Noteo()
    try:
        noteo.start()
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
        noteo._handle_event(QuitEvent())
    print "...exiting noteo"



if __name__ == '__main__':
    run_noteo()
