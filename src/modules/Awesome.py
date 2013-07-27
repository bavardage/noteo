from subprocess import Popen

from Noteo import *

class Awesome(NoteoModule):
    config_spec = {
        'command': 'string(default=\'infobox.text=\"%s %c\"\')',
        #%s summary, %c content, %i icon
        }
    def init(self):
        pass

    def handle_NotificationEvent(self, event):
        self.do_output(event.get_summary(), event.get_content(),
                       event.get_icon())

    def do_output(self, summary, content, icon):
        summary = summary.replace('"', r'\"').replace("'", r"\'")
        content = content.replace('"', r'\"').replace("'", r"\'")
        command = self.config['command']
        command = command.replace("%s", summary)
        command = command.replace("%c", content)
        #command = command.replace("%i", icon)
        command = command.replace("\n", " ")
        self.awesome_client(command)

    def awesome_client(self, command):
        to_call = "echo '%s' | awesome-client" % command
        p = Popen(to_call, shell=True)

module = Awesome
