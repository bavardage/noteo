#!/usr/bin/env python

import os
import imaplib
import re

from Noteo import *

class Mails(object):

    def __init__(self, server, user, password, mailbox, server_name="mailserver", content_lines=2):
        """ user mail stuff variables: """
        self.server = server
        self.user = user
        self.password = password
        self.mailbox = mailbox
        self.content_lines = content_lines
        self.tmp_file = "/tmp/.mails." + server_name + "-" + str(os.getuid()) + ".cache"


    def get_unread(self, connect_over_ssl = True):
        """ access IMAP-server: input dict w/ deleted mails; output: dict w/ new mails """
        if connect_over_ssl != 0:
            m = imaplib.IMAP4_SSL(self.server)
        else:
            m = imaplib.IMAP4(self.server)
        m.login(self.user, self.password)
        m.select(self.mailbox)
        
        m.expunge()

        data_dict=dict()
        print m
        alt_1, unread = m.search(None,'(UNSEEN UNDELETED)')
        print unread
        for num in unread[0].split():
            print num
            alt_2, body = m.fetch(num,'(BODY[HEADER.FIELDS (DATE FROM SUBJECT)] BODY[TEXT])')
            body.remove(')')

            body_text = re.compile('^.*BODY\[TEXT\].*$')    ##  check for order of text and header, then sort 
            if body_text.match(body[0][0]) == None:         ##  first header[0], then text[1]
                data_1 = body[0][1].split('\r\n')
                data_2 = body[1][1].split('\n')
            else:                                           ##  first text[0], then header[1]
                data_1 = body[1][1].split('\r\n')
                data_2 = body[0][1].split('\n')
            data_1 = data_1[0:3]
            data_1.sort()     ##  Date, From, Subject

            data_3 = []     ##  mail content
            content_filter = re.compile('^Content-|--=20|>=20|.*charset|--Sig|-----', re.M)
            for i in data_2:
                if content_filter.match(i) == None:
                    data_3.append(unicode(i, 'latin-1'))
            data_3 = data_3[0:self.content_lines]
            del data_2
            try:
                data_dict[int(num)] = [data_1[0].split(': ',1)[1].rsplit('+')[0].rsplit('-')[0], data_1[1].split(':',1)[1], data_1[2].split(':',1)[1], '', data_3]
            except IndexError:
                pass
            m.store(num, "FLAGS", '(UNSEEN)')
        m.close()
        m.logout
        return data_dict


class IMAPChecker(NoteoModule):
    config_spec = {
        'server': 'string(default=imap.example.com)',
        'username': 'string(default=username)',
        'password': 'string(default=password)',
        'mailbox': 'string(default=inbox)',
        'serverName': 'string(default=imapserver)',
        'linesOfContent': 'integer(default=2)',
        'checkInterval': 'float(default=120.0)',
        'checkOverSSL': 'boolean(default=True)',
        }
    def init(self):
        self.mails = Mails(self.config['server'],
                           self.config['username'],
                           self.config['password'],
                           self.config['mailbox'],
                           self.config['serverName'],
                           self.config['linesOfContent'],
                           )
        self.update_event = RecurringFunctionCallEvent(self.noteo,
                                                       self.check,
                                                       self.config['checkInterval']
                                                       )
        self.update_event.add_to_queue()
                                                       

    def check(self):
        data = self.mails.get_unread(self.config['checkOverSSL'])
        if len(data) > 0:
            NotificationEvent(self.noteo,
                              0,
                              "You have new messages",
                              "%i new message%s on %s" % (
                    len(data), ("s" if len(data) > 1 else ""),
                    self.config['username']),
                              'dialog-info'
                              )
            ).add_to_queue()
        return True

module = IMAPChecker
