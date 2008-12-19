import libgmail

from Noteo import *

class GmailCheck(NoteoModule):
    config_spec = {
        'checkInterval': 'float(default=120)',
        'usernames': 'list(default=list(username1, username2))',
        'passwords': 'list(default=list(password1, password2))',
        }
    gmail_accounts = None
    def init(self):
        self.update_event = RecurringFunctionCallEvent(self.noteo,
                                                  self.check, 
                                                  self.config['checkInterval']
                                                  )
        self.noteo.add_event_to_queue(self.update_event)
        self.login_event = FunctionCallEvent(self.noteo,
                                             1,
                                             self.login
                                             )
        self.noteo.add_event_to_queue(self.login_event)
        
        check_mail_menu_item = CreateMenuItemEvent(self.noteo,
                                                   "Check mail now",
                                                   self.check,
                                                   icon='stock_mail'
                                                   )
        self.noteo.add_event_to_queue(check_mail_menu_item)

    def check(self):
        self.noteo.logger.debug("Checking mail...")
        if self.gmail_accounts is None:
            self.login()
        for account in self.gmail_accounts:
            try:
                unread = account.getUnreadMessages()
            except:
                unread = []
                self.gmail_accounts = None
            for message in unread:
                summary = "New message on %s" % account.name
                content = message.subject
                notification = NotificationEvent(self.noteo,
                                                 0,
                                                 summary,
                                                 content,
                                                 'dialog-info'
                                                 )
                self.noteo.add_event_to_queue(notification)
        return True
        
    def login(self):
        gmail_accounts = []
        for i in range(len(self.config['usernames'])):
            try:
                username = self.config['usernames'][i]
                password = self.config['passwords'][i]
                gmail_accounts.append(libgmail.GmailAccount(username, password))
            except:
                pass
        for account in gmail_accounts:
            try:
                account.login()
            except libgmail.GmailLoginFailure:
                self.noteo.logger.error("Incorrect username/password")
        self.gmail_accounts = gmail_accounts
            
module = GmailCheck
