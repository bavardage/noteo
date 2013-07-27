import email
from email.header import decode_header
import imaplib
import re
import time
import threading
from xml.sax.saxutils import escape

from Noteo import *


class MailTracker:
    def __init__(self, server, port, ssl, username, password, interval, retries=1):
        self._unread = []

        self.server = server
        self.port = port
        self.ssl = ssl
        self.username = username
        self.password = password
        self.interval = interval
        self.retries = retries
        self.last_unseen = set()

        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._check)
        self.thread.daemon = True
        self.thread.start()

    def _login(self):
        if self.ssl:
            conn = imaplib.IMAP4_SSL(self.server, self.port)
        else:
            conn = imaplib.IMAP4(self.server, self.port)
        conn.login(self.username, 
                   self.password)
        conn.select(readonly=1) # Select inbox or default namespace
        return conn

    def _get_unseen_uids(self, conn):
        (retcode, messages) = conn.search(None, '(UNSEEN)')
        if retcode != 'OK':
            raise imaplib.IMAP4.error("Error return code: %s" % retcode)

        messages = messages[0].strip()
        if len(messages):
            messages = messages.split(' ')
            (retcode, data) = conn.fetch(",".join(messages),'(UID)')
            if retcode != 'OK':
                raise imaplib.IMAP4.error("Error return code: %s" % retcode)
        else:
            data = []

        uid_extracter = re.compile(r'\d* \(UID (\d*)')
        unseen = set()
        for item in data:
            ret = uid_extracter.match(item).group(1)
            unseen.add(int(ret))
        new = unseen - self.last_unseen
        self.last_unseen = unseen & self.last_unseen
        return new

    def _check(self):
        while True:
            for i in range(self.retries + 1):
                try:
                    conn = self._login()

                    #Get UIDs
                    new = self._get_unseen_uids(conn)

                    for uid in new:
                        retcode, data = conn.uid('FETCH', uid, '(RFC822)')#BODY[HEADER.FIELDS (DATE FROM SUBJECT)] BODY[TEXT])')
                        if retcode != 'OK':
                            raise imaplib.IMAP4.error("Error return code: %s" % retcode)
                        content = email.message_from_string(data[0][1])
                        with self.lock:
                            self._unread.append(content)
                        self.last_unseen.add(uid)
                    conn.close()
                    conn.logout()
                    break
                except BaseException as e:
                    print("Error mail", e)

            time.sleep(self.interval)

    def check(self):
        with self.lock:
            tmp = self._unread
            self._unread = []
        return tmp

class IMAPCheck(NoteoModule):
    config_spec = {
        'checkInterval': 'float(default=120)',
        'notificationTimeout': 'float(default=10)',
        'linesOfContent': 'integer(default=2)',
        'username': 'list(default=list(username1, username2))',
        'password': 'list(default=list(password1, password2))',
        'server': 'list(default=list(password1, password2))',
        'mailbox': 'list(default=list(inbox, inbox))',
        'port': 'list(default=list(password1, password2))',
        'ssl': 'list(default=list(password1, password2))',
    }
    connections = None

    header_line = '<span size=\"large\"><b>You have <span foreground=\"red\">%d</span> new message%s (%s@%s)</b></span>\n'
    from_line = '<span size=\"large\"><b>From: %s</b></span>\n'
    subject_line = 'Subject: %s\n'
    def init(self):
        update_event = FunctionCallEvent(self.check)
        update_event.recurring_delay = 2
        self.noteo.add_event(update_event)

        self.noteo.add_event(FunctionCallEvent(self.create_connections))

        self.noteo.add_event(CreateMenuItemEvent("Check mail now",
                                                 self.check,
                                                 icon='stock_mail')) #TODO: Add conditions to handle this


    def decode(self, string, join=" ", max_items=0, max_len=0):
        decoded_header = decode_header(string.strip())

        content = []
        for line in decoded_header:
            max_items = max_items - 1
            if max_items == 0:
                break

            tmp = line[0]
            if line[1] is not None:
                tmp = tmp.decode(line[1])
            if max_len:
                tmp = (tmp[:max_len] + '..') if len(tmp) > max_len else tmp
            content.append(tmp)
        return join.join(content)

    def get_content(self, message):
        if self.config['linesOfContent'] == 0:
            return ""
        text = ""
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                text = part.get_payload(decode=True)
                text = text.decode(part.get_content_charset('utf-8'))
                break
            elif part.get_content_type() == "text/html":
                text = part.get_payload(decode=True)
                text = text.decode(part.get_content_charset('utf-8'))
        text = text.replace('\r', '\n')
        text = [x.strip() for x in text.split('\n') if len(x.strip())]
        if len(text) > self.config['linesOfContent']:
            text = text [:self.config['linesOfContent']]
        text = "\n".join(text)
        text = re.sub('<[^<]+?>', '', text)
        text = re.sub('&[^;]*;', '', text)
        text = re.sub('<', '', text)
        text = re.sub('>', '', text)
        text = re.sub('&', '', text)
        return text

    def check(self):
        self.noteo.logger.debug("Checking mail...")
        if self.connections is None:
            return
        for i in range(len(self.connections)):
            conn = self.connections[i]
            unread = conn.check()
            if len(unread) == 0:
                continue
            suffix = ''
            if len(unread) > 1:
                suffix = 's'
            summary = self.header_line % (len(unread), suffix, conn.username, conn.server)

            content = ""
            for message in unread:
                _from = message['from'].split(' ')
                _from[0] = self.decode(_from[0].strip('"'))
                _subject = self.decode(message['subject'])

                content += self.from_line % escape(_from[0])
                content += self.subject_line % escape(_subject)
                content += "<i>%s</i>\n\n" % escape(self.get_content(message))

            self.noteo.add_event(NotificationEvent(summary,
                                                   content,
                                                   'mail_new',
                                                   timeout=self.config['notificationTimeout']))
        return True

    def create_connections(self):
        server = self.config['server']
        port = self.config['port']
        ssl = self.config['ssl']
        username = self.config['username']
        password = self.config['password']
        password = self.config['password']

        connections = []
        for i in range(len(server)):
            connections.append(MailTracker(server[i], port[i], ssl[i], username[i], password[i], float(self.config['checkInterval'])))
        self.connections = connections
        self.check()
            
module = IMAPCheck
