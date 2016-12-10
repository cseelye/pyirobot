#!/usr/bin/env python2.7
"""
A python library for controlling an iRobot cleaning robot
Only the Roomba 980 is tested; the Roomba 960 should work and possibly the Braava 300
"""

import collections
import datetime
from enum import Enum
import json
import requests
import socket
import struct

# Disable SSL warning from requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class CarpetBoost(Enum):
    Auto = 0
    Eco = 16
    Perf = 80
    __order__ = "Eco Perf Auto"

class CleaningPasses(Enum):
    Auto = 0
    One = 1024
    Two = 1025
    __order__ = "One Two Auto"

class FinishWhenBinFull(Enum):
    On = 0
    Off = 32
    __order__ = "Off On"

class EdgeClean(Enum):
    On = 0
    Off = 2
    __order__ = "Off On"

class RobotError(Exception):
    """ Exception thrown when there is an error """

    def __init__(self, errorCode):
        super(RobotError, self).__init__()
        self.errorCode = errorCode
    def __str__(self):
        return "Error code {}".format(self.errorCode)

class Robot(object):
    """
    This object represents an iRobot cleaning robot
    """

    @staticmethod
    def GetPassword(robotIP):
        """
        Get the password for this robot

        Before calling this method, place the robot on its dock and then hold down the home button for 3-4 seconds,
        until the LEDs illuminate and the robot emits a series of tones.  Then quickly call this method

        Returns:
            The robot password (str)
        """
        result = requests.post("https://{}/umi".format(robotIP),
                                data=json.dumps({"do" : "get",
                                                 "args" : ["passwd"],
                                                 "id" : 0}),
                                headers={"Content-Type" : "application/json"},
                                verify=False)
        res = result.json()
        if "err" in res:
            raise RobotError(res["err"])
        return res["ok"]["passwd"]

    @staticmethod
    def GetBLID(robotIP, password):
        """
        Get this robot's BLID, which you need for making cloud-based calls to the robot

        Returns:
            The robot BLID (str)
        """
        result = requests.post("https://{}/umi".format(robotIP),
                                data=json.dumps({"do" : "get",
                                                 "args" : ["sys"],
                                                 "id" : 0}),
                                auth=("user", password),
                                headers={"Content-Type" : "application/json"},
                                verify=False)
        res = result.json()
        if "err" in res:
            raise RobotError(res["err"])
        return "".join([i[2:] for i in map(hex, res["ok"]["blid"])])

    def __init__(self, robotIP, robotPassword):
        self.ip = robotIP
        self.password = robotPassword
        self.nextID = 1

    def _GetRequestID(self):
        """
        Get a unique request ID

        Returns:
            A request ID (int)
        """
        rid = self.nextID
        self.nextID += 1
        return rid

    def _PostToRobot(self, cmd, args):
        """
        Send a command to the robot and get the response

        Args:
            cmd:    the "do" argument for the request (str)
            args:   the "args" argument for the request (str or list)

        Returns:
            The JSON response parsed into a dictionary (dict)
        """
        if isinstance(args, basestring) or not isinstance(args, collections.Iterable):
            args = [args]
        result = requests.post("https://{}/umi".format(self.ip),
                                data=json.dumps({"do" : cmd,
                                                 "args" : args,
                                                 "id" : self._GetRequestID()}),
                                auth=("user", self.password),
                                headers={"Content-Type" : "application/json"},
                                verify=False)
#        print result.request.body
#        print result.text
        res = result.json()
        if "err" in res:
            raise RobotError(res["err"])
        return res["ok"]

    def StartCleaning(self):
        """
        Start a cleaning cycle
        """
        self._PostToRobot("set", ["cmd", {"op" : "start"}])

    def PauseCleaning(self):
        """
        Pause the current cleaning cycle

        This command has no effect if the robot is not currently cleaning
        """
        self._PostToRobot("set", ["cmd", {"op" : "pause"}])

    def ResumeCleaning(self):
        """
        Resume a paused cleaning cycle

        This command has no effect if the robot is not currently paused
        """
        self._PostToRobot("set", ["cmd", {"op" : "resume"}])

    def EndCleaning(self):
        """
        End the current cleaning cycle

        This command has no effect if the robot is not currently cleaning or paused
        """
        self._PostToRobot("set", ["cmd", {"op" : "stop"}])

    def ReturnHome(self):
        """
        Send the robot back to the home dock

        The robot must be stopped or paused first
        """
        self._PostToRobot("set", ["cmd", {"op" : "dock"}])

    def GetCleaningPreferences(self):
        """
        Get this robot's cleaning preferences

        Returns:
            A dictionary of preferences (dict)
        """
        result = self._PostToRobot("get", "prefs")
        prefs = {}
        for key, value in result.iteritems():
            if key == "flags":
                continue
            prefs[key] = value

        # Decode the flags
        flags = result["flags"]
        for conf in (CarpetBoost, CleaningPasses, FinishWhenBinFull, EdgeClean):
            test = flags & max(conf, key=lambda x: x.value).value
            for itr in conf:
                if test == itr.value:
                    prefs[conf.__name__[0].lower() + conf.__name__[1:]] = itr.name
                    break
        return prefs

    def GetTime(self):
        """
        Get the time this robot is set to

        Returns:
            The robot's time (datetime object)
        """
        now = datetime.datetime.now()
        result = self._PostToRobot("get", "time")
        return datetime.datetime(now.year, now.month, now.day, result["h"], result["m"])

    def GetSchedule(self):
        """
        Get the cleaning schedule for this robot
        
        Returns:
            A dictionary representing the schedule (dict)
        """
        result = self._PostToRobot("get", "week")
        return result

    def GetMission(self):
        """
        Get the real-time status and position of the robot

        Returns:
            A dictionary with the current robot status (dict)
        """
        return self._PostToRobot("get", "mssn")

    def GetWiFiDetails(self):
        """
        Get detailed information about the robot's WiFi connection

        Returns:
            A dictionary of wifi information (dict)
        """
        res = self._PostToRobot("get", "wlstat")

        # Transform the data to be more user friendly and closer to how the app presents it
        res["bssid"] = ":".join([i[2:] for i in map(hex, res["bssid"])])
        res["dhcp"] = True if res["dhcp"] == 1 else False
        res["ip_address"] = socket.inet_ntoa(struct.pack("I", res.pop("addr")))
        res["subnet_mask"] = socket.inet_ntoa(struct.pack("I", res.pop("mask")))
        res["router"] = socket.inet_ntoa(struct.pack("I", res.pop("gtwy")))
        res["dns1"] = socket.inet_ntoa(struct.pack("I", res.pop("dns1")))
        res["dns2"] = socket.inet_ntoa(struct.pack("I", res.pop("dns2")))
        res["signal_strength"] = res.pop("strssi")
        res["security_type"] = "WPA2" if res["sec"] == 4 else str(res["sec"])
        res.pop("sec")

        return res

    def GetWiFiStatus(self):
        """
        Get a simple check of the robot's WiFi status

        Returns:
            A dictionary of status (dict)
        """
        res = self._PostToRobot("get", "wllaststat")

        # Transform data to better match GetWiFiDetails
        res["signal_strength"] = res.pop("strssi")
        return res

    def GetCloudConfig(self):
        return self._PostToRobot("get", "cloudcfg")

    def GetSKU(self):
        return self._PostToRobot("get", "sku")

    def GetSys(self):
        return self._PostToRobot("get", "sys")

    def GetBBRun(self):
        return self._PostToRobot("get", "bbrun")

    def GetWiFiSettings(self):
        return self._PostToRobot("get", "wlconfig")






