
import urllib
import urllib2
import os.path
import re
from xml.etree.ElementTree import XMLTreeBuilder

from Noteo import *

class GoogleReaderAPI:
    user_agent = 'Noteo'
    urls = {
        'google': 'http://www.google.com',
        'login': 'https://www.google.com/accounts/ClientLogin',
        'reader': 'http://www.google.com/reader',
        'subscription-list': '/api/0/subscription/list',
        'unread-list': '/atom/user/-/state/com.google/reading-list',
        'unread-count': '/api/0/unread-count?all=true',
        }
    def __init__(self, email, password, error=lambda x:x):
        self.email = email
        self.password = password
        self.error = error
        self.sid = None

    def login(self):
        if self.sid:
            return
        header = {'User-agent': self.user_agent}
        post_data = urllib.urlencode({'Email': self.email,
                                      'Passwd': self.password,
                                      'service': 'reader',
                                      'source': self.user_agent,
                                      'continue': self.urls['google'],
                                      })
        request = urllib2.Request(self.urls['login'], post_data, header)
        try:
            f = urllib2.urlopen(request)
            result = f.read()
            self.sid = re.search('SID=(\S*)', result).group(1)
        except:
            self.error("Error logging in")
            self.sid = None
            raise
    
    def get_results(self, url):
        if not self.sid:
            self.login()
        if not self.sid:
            self.error("Didn't log in")
            return None
        header = {'User-agent': self.user_agent}
        header['Cookie']='Name=SID;SID=%s;Domain=.google.com;Path=/;Expires=160000000000' % self.sid
        request = urllib2.Request(url, None, header)
        try:
            f = urllib2.urlopen(request)
            return f.read()
        except:
            self.error("Error getting data")
            raise
            return None

    def get_unread(self):
        url = self.urls['reader'] + self.urls['unread-list']
        data = self.get_results(url)
        return data

    def get_subscriptions(self):
        url = self.urls['reader'] + self.urls['subscription-list']
        data = self.get_results(url)
        tree = XMLTreeBuilder()
        tree.feed(data)
        root_object = tree.close()
        li = root_object.getchildren()[0]
        feeds = {}
        for obj in li:
            feed_id = obj.getchildren()[0].text
            title = obj.getchildren()[1].text
            feeds[feed_id] = title
        return feeds

    def get_unread_count(self):
        url = self.urls['reader'] + self.urls['unread-count']
        data = self.get_results(url)
        tree = XMLTreeBuilder()
        tree.feed(data)
        root_object = tree.close()
        li = root_object.getchildren()[1]
        counts = []
        for obj in li:
            feed_id, count, timestamp = \
                [ele.text for ele in obj.getchildren()]
            counts.append((feed_id, count, timestamp))
        return counts

class GoogleReader(NoteoModule):
    config_spec = {
        'checkInterval': 'float(default=600)',
        'email': 'string(default=username@gmail.com)',
        'password': 'string(default=password)',
        }
    def init(self):
        self.client = GoogleReaderAPI(self.config['email'],
                                      self.config['password'],
                                      self.error
                                      )
        self.icon = os.path.join(self.path, 'rssicon.png')
        self.update_event = RecurringFunctionCallEvent(self.noteo,
                                                       self.check,
                                                       self.config['checkInterval'],
                                                       )
        self.update_event.add_to_queue()
        update_menu_item = CreateMenuItemEvent(self.noteo,
                                               "Check GoogleReader now",
                                               self.check,
                                               icon=self.icon,
                                               )
        update_menu_item.add_to_queue()

    def error(self, error):
        self.noteo.logger.error("Google Reader Errored: %s" % error)

    def check(self):
        feeds = self.client.get_subscriptions()
        unread = self.client.get_unread_count()
        total_unread = 0
        items = []
        for feedid, count, timestamp in unread:
            if feedid in feeds:
                count = int(count)
                items.append((feeds[feedid], 
                              count))
                total_unread += count
        if total_unread:
            plural = lambda x: ('s' if x > 1 else '')
            summary = '%s Unread Item%s' % (total_unread, 
                                                  plural(total_unread))
            markup = ''
            for name, count in items:
                markup += '<b>%s:</b> %s unread item%s\n' % (name,
                                                                   count,
                                                                   plural(count)
                                                                   )
        notification = NotificationEvent(self.noteo,
                                         0,
                                         summary,
                                         markup,
                                         self.icon,
                                         )
        notification.add_to_queue()
        return True
                              
module = GoogleReader
