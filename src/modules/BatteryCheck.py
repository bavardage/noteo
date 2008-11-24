#!/usr/bin/env python

import re
import commands

from Noteo import *

class BatteryCheck(NoteoModule):
    config_spec = {
        'lowPercentage': 'integer(default=10)',
        'criticalPercentage': 'integer(default=5)',
        'pollInterval': 'float(default=60)',
        }
    notified_low = False
    notified_critical = False
    state = (100, True)
    def init(self):
        if self.config['lowPercentage'] < self.config['criticalPercentage']:
            self.noteo.logger.warning(
                "The low percentage is lower than critical percentage" +
                " - swapping")
            self.config['lowPercentange'], self.config['criticalPercentage'] = \
                self.config['criticalPercentage'], self.config['lowPercentage']
        self.find_percentage = re.compile(r'.+?([0-9]+?)\%.*?')
        self.is_discharging = re.compile(r'.*dis.*')
        self.check_event = RecurringFunctionCallEvent(self.noteo,
                                                      self.check_battery,
                                                      self.config['pollInterval']
                                                      )
        self.noteo.add_event_to_queue(self.check_event)
        
    def check_battery(self):
        self.noteo.logger.debug("Current state is %s %s" % self.state)
        status = commands.getoutput('acpi')
        percentage = 100 #default
        charging = False
        if self.find_percentage.match(status):
            percentage = int(self.find_percentage.match(status).groups()[0])
        if not self.is_discharging.match(status):
            charging = True
        if charging:
            self.notified_low = False
            self.notified_critical = False
            if not self.state[1]: #if wasn't previously charging
                notification = NotificationEvent(self.noteo,
                                                 0,
                                                 "AC Power",
                                                 "AC power has been plugged in",
                                                 'gpm-ac-adapter'
                                                 )
                self.noteo.add_event_to_queue(notification)
            self.noteo.logger.debug("Previously was %s, now %s" %
                                    (self.state[1], charging))
        else:
            if percentage < self.config['criticalPercentage'] \
                    and not self.notified_critical:
                self.notified_critical = True
                notification = NotificationEvent(self.noteo,
                                                 0,
                                                 "Battery Critical",
                                                 "Battery charge is only %s%%" % percentage,
                                                 'battery'
                                                 )
                self.noteo.add_event_to_queue(notification)
            elif percentage < self.config['lowPercentage'] \
                    and not self.notified_low:
                self.notified_low = True
                notification = NotificationEvent(self.noteo,
                                                 0,
                                                 "Battery Low",
                                                 "Battery charge is at %s%%" % percentage,
                                                 'battery'
                                                 )
                self.noteo.add_event_to_queue(notification)
        self.noteo.logger.debug("Setting status to percentage: %s, charging %s" %
                         (percentage, charging))
        self.state = (percentage, charging)
        return True

module = BatteryCheck
