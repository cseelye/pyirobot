#!/usr/bin/env python2.7
"""
A python library for controlling an iRobot cleaning robot
Only the Roomba 980 is tested; the Roomba 960 should work and possibly the Braava Jet
"""

import calendar
import collections
import datetime
from enum import Enum
import json
import requests
import socket
import struct

# Disable SSL warning from requests - the Roomba's SSL certificate is self signed
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Monkey patch the json module to be able to encode Enums and datetime.time
_json_default = json.JSONEncoder().default
def _encode_enum(self, obj):
    if isinstance(obj, Enum):
        return obj.name
    if isinstance(obj, datetime.time):
        return str(obj)
    return _json_default(self, obj)
json.JSONEncoder.default = _encode_enum

class CarpetBoost(Enum):
    Unknown = -1
    Auto = 0
    Eco = 16
    Perf = 80

    @classmethod
    def PrefName(cls):
        return "carpetBoost"

class CleaningPasses(Enum):
    Unknown = -1
    Auto = 0
    One = 1024
    Two = 1025

    @classmethod
    def PrefName(cls):
        return "cleaningPasses"

class FinishWhenBinFull(Enum):
    Unknown = -1
    On = 0
    Off = 32

    @classmethod
    def PrefName(cls):
        return "finishWhenBinFull"

class EdgeClean(Enum):
    Unknown = -1
    On = 0
    Off = 2

    @classmethod
    def PrefName(cls):
        return "edgeClean"

class MissionState(Enum):
    Unknown = -1
    BinFull = 1
    BinMissing = 2
    Normal = 4
    Resuming = 8

class RobotStatus(Enum):
    Unknown = "unknown"
    Idle = "none"
    Cleaning = "run"
    Stopped = "stop"
    Charging = "charge"
    Resuming = "resume"
    ReturningHome = "hmPostMsn"
    Cancelling = "hmUsrDock"
    Stuck = "stuck"

class BinStatus(Enum):
    Unknown = -1,
    Normal = 0,
    Full = 1,
    Missing = 2

class ReadyStatus(Enum):
    Unknown = -1
    Ready = 0
    Cliff = 1
    BothWheelsDropped = 2
    LeftWheelDropped = 3
    RightWheelDropped = 4
    BinMissing = 7

# From http://homesupport.irobot.com/app/answers/detail/a_id/9024/~/roomba-900-error-messages
_ErrorMessages = {
    1 : "Roomba is stuck with its left or right wheel hanging down.",
    2 : "The debris extractors can't turn.",
    5 : "The left or right wheel is stuck.",
    6 : "The cliff sensors are dirty, it is hanging over a drop, or it is stuck on a dark surface.",
    8 : "The fan is stuck or its filter is clogged.",
    9 : "The bumper is stuck, or the bumper sensor is dirty.",
    10: "The left or right wheel is not moving.",
    11: "Roomba has an internal error.",
    14: "The bin has a bad connection to the robot.",
    15: "Roomba has an internal error.",
    16: "Roomba has started while moving or at an angle, or was bumped while running.",
    17: "The cleaning job is incomplete.",
    18: "Roomba cannot return to the Home Base or starting position."
}

_MissionCycleToCleaningPasses = {
    "quick" : CleaningPasses.One,
    "clean" : CleaningPasses.Two
}

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
        post_data = json.dumps({"do" : cmd,
                                "args" : args,
                                "id" : self._GetRequestID()})
#        print post_data
        result = requests.post("https://{}/umi".format(self.ip),
                                data=post_data,
                                auth=("user", self.password),
                                headers={"Content-Type" : "application/json"},
                                verify=False)
#        print result.request.body
#        print result.text
        res = result.json()
        if "err" in res:
            raise RobotError(res["err"])
        return res["ok"]

    def _DecodePreferencesFlags(self, flags):
        """
        Decode the 'flags' field from a preferences call into individual
        preferences enums.

        Args:
            flags:  the integer flags value (int)

        Returns:
            A dictionary of preferences (dict)
        """
        prefs = {}
        for conf in (CarpetBoost, CleaningPasses, FinishWhenBinFull, EdgeClean):
            pref_name = unicode(conf.PrefName())
            test = flags & max(conf, key=lambda x: x.value).value
            try:
                prefs[pref_name] = conf(test)
            except ValueError:
                prefs[pref_name] = conf["Unknown"]
        return prefs

    def _EncodePreferencesFlags(self, prefs):
        """
        Encode a dictionary of preferences into a single 'flags' integer

        Args:
            prefs: a dictionary of preferences (dict)

        Returns:
            An integer representing the value of the preferences (int)
        """
        flags = 0
        for conf in (CarpetBoost, CleaningPasses, FinishWhenBinFull, EdgeClean):
            pref_name = conf.PrefName()
            assert pref_name in prefs, "{} must be in prefs".format(pref_name)
            assert isinstance(prefs[pref_name], conf), "{} must be a {} enum".format(pref_name, conf.__name__)
            flags += prefs[pref_name].value
        return flags

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
        prefs.update(self._DecodePreferencesFlags(result["flags"]))
        return prefs

    def GetTime(self):
        """
        Get the time this robot is set to

        Returns:
            A dictionary with the time of day and day of week (dict)
        """
        result = self._PostToRobot("get", "time")
        day_idx = [idx for idx, day in enumerate(calendar.day_abbr) if day.lower() == result["d"]][0]
        return {
            "time" : datetime.time(result["h"], result["m"]),
            "weekday" : calendar.day_name[day_idx]
        }

    def GetSchedule(self):
        """
        Get the cleaning schedule for this robot

        Returns:
            A dictionary representing the schedule per day (dict)
        """
        res = self._PostToRobot("get", "week")
        schedule = {}
        for idx in xrange(7):
            cal_day_idx = idx - 1
            if cal_day_idx < 0:
                cal_day_idx = 6
            schedule[calendar.day_name[cal_day_idx]] = {
                "clean" : True if res["cycle"][idx] == "start" else False,
                "startTime" : datetime.time(res["h"][idx], res["m"][idx])
            }
        return schedule

    def GetMission(self):
        """
        Get the real-time status and position of the robot

        Returns:
            A dictionary with the current robot status (dict)
        """
        res = self._PostToRobot("get", "mssn")

        # Transform the data to be more user friendly and closer to how the app presents it
        res[u"batteryPercentage"] = res.pop("batPct")

        if res["expireM"] <= 0:
            res.pop("expireM")
        else:
            res[u"minutesUntilMissionCancelled"] = res.pop("expireM")

        res[u"missionElapsedMinutes"] = res.pop("mssnM")

        try:
            res[u"readyStatus"] = ReadyStatus(res["notReady"])
        except ValueError:
            res[u"readyStatus"] = ReadyStatus.Unknown
        if res["readyStatus"] != ReadyStatus.Unknown:
            res.pop("notReady")

        res[u"robotPosition"] = res.pop("pos")

        if res["rechrgM"] <= 0:
            res.pop("rechrgM")
        else:
            res[u"rechargeMinutesRemaining"] = res.pop("rechrgM")

        res[u"missionCoveredSquareFootage"] = res.pop("sqft")

        res[u"binStatus"] = BinStatus.Normal
        if res["flags"] & MissionState.BinFull.value == MissionState.BinFull.value:
            res[u"binStatus"] = BinStatus.Full
        elif res["flags"] & MissionState.BinMissing.value == MissionState.BinMissing.value:
            res[u"binStatus"] = BinStatus.Missing

        try:
            res[u"robotStatus"] = RobotStatus(res["phase"])
        except ValueError:
            res[u"robotStatus"] = RobotStatus.Unknown
        if res["robotStatus"] == RobotStatus.Cleaning and res["flags"] & MissionState.Resuming.value == MissionState.Resuming.value:
            res[u"robotStatus"] = RobotStatus.Resuming

        if res["robotStatus"] != RobotStatus.Unknown:
            res.pop("flags")
            res.pop("phase")

        if res["error"] == 0:
            res.pop("error")
        elif res["error"] in _ErrorMessages:
            res[u"errorMessage"] = _ErrorMessages[res["error"]]

        if res["cycle"] == "none":
            res.pop("cycle")
        elif res["cycle"] in _MissionCycleToCleaningPasses:
            res["cycle"] = _MissionCycleToCleaningPasses[res["cycle"]]

        return res

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
        res["ipAddress"] = socket.inet_ntoa(struct.pack("I", res.pop("addr")))
        res["subnetMask"] = socket.inet_ntoa(struct.pack("I", res.pop("mask")))
        res["router"] = socket.inet_ntoa(struct.pack("I", res.pop("gtwy")))
        res["dns1"] = socket.inet_ntoa(struct.pack("I", res.pop("dns1")))
        res["dns2"] = socket.inet_ntoa(struct.pack("I", res.pop("dns2")))
        res["signalStrength"] = res.pop("strssi")
        res["securityType"] = "WPA2" if res["sec"] == 4 else str(res["sec"])
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
        res["signalStrength"] = res.pop("strssi")
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

    def GetStatus(self):
        """
        Get a combined view of preferences and mission in a single call
        """
        return {
            "cleaningPreferences" : self.GetCleaningPreferences(),
            "mission" : self.GetMission()
        }

    def SetCleaningPreferences(self, prefs):
        """
        Set the cleaning preferences for this robot. All of the fields are
        required in the preferences dictionary, even if you are not changing
        them.
        
        The easiest way to use this function is to call GetCleaningPreferences,
        modify the result, and use that as the input to this function.

        Args:
            prefs:  a dictionary of preferences
        """
        newprefs = collections.OrderedDict([
            ("flags", self._EncodePreferencesFlags(prefs)),
            ("lang", prefs["lang"]),
            ("timezone", prefs["timezone"]),
            ("name", prefs["name"])
        ])
        self._PostToRobot("set", ["prefs", newprefs])

    def SetCarpetBoost(self, newValue):
        """
        Set the Carpet Boost cleaning preference

        Args:
            newValue:  the value to set (CarpetBoost)
        """
        assert isinstance(newValue, CarpetBoost), "newValue must be a CarpetBoost enum value"
        prefs = self.GetCleaningPreferences()
        prefs[CarpetBoost.PrefName()] = newValue
        self.SetCleaningPreferences(prefs)

    def SetCleaningPasses(self, newValue):
        """
        Set the Cleaning Passes cleaning preference

        Args:
            newValue:  the value to set (CleaningPasses)
        """
        assert isinstance(newValue, CleaningPasses), "newValue must be a CleaningPasses enum value"
        prefs = self.GetCleaningPreferences()
        prefs[CleaningPasses.PrefName()] = newValue
        self.SetCleaningPreferences(prefs)

    def SetFinishWhenBinFull(self, newValue):
        """
        Set the Finish When Bin Full cleaning preference

        Args:
            newValue:  the value to set (FinishWhenBinFull)
        """
        assert isinstance(newValue, FinishWhenBinFull), "newValue must be a FinishWhenBinFull enum value"
        prefs = self.GetCleaningPreferences()
        prefs[FinishWhenBinFull.PrefName()] = newValue
        self.SetCleaningPreferences(prefs)

    def SetEdgeClean(self, newValue):
        """
        Set the Edge Clean cleaning preference

        Args:
            newValue:  the value to set (EdgeClean)
        """
        assert isinstance(newValue, EdgeClean), "newValue must be an EdgeClean enum value"
        prefs = self.GetCleaningPreferences()
        prefs[EdgeClean.PrefName()] = newValue
        self.SetCleaningPreferences(prefs)

    def SetTimezone(self, newValue):
        """
        Set the robot's timezone. The time zone must be a tz database name.
        https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

        For instance, common US time zones:
            Pacific time:  'America/Los_Angeles' or 'US/Pacific'
            Mountain time: 'America/Denver' or 'US/Mountain'
            Central time:  'America/Chicago' or 'US/Central'
            Eastern time:  'America/New_York' or 'US/Eastern'

        Args:
            newValue:   the time zone name (str)
        """
        prefs = self.GetCleaningPreferences()
        prefs[u"timezone"] = newValue
        self.SetCleaningPreferences(prefs)

    def SetTime(self, newTime):
        """
        Set the robot's time. The robot only cares about weekday, hour and
        minute, so those are the only fields that need to be accurate in
        the datetime object.

        Args:
            newTime:    the time to set the robot to (datetime)
        """
        weekday = newTime.isoweekday()
        if weekday > 6:
            weekday = 0
        self._PostToRobot("set", ["time", collections.OrderedDict([
            ("d", weekday),
            ("h", newTime.hour),
            ("m", newTime.minute)])
        ])

    def SetTimeNow(self):
        """
        Set the robot's time to the current time
        """
        self.SetTime(datetime.datetime.now())

    def SetSchedule(self, newSchedule):
        """
        Set the cleaning schedule for this robot.
        The easiest way to use this function is to call GetSchedule, modify
        the result, and use that as the input to this function

        Args:
            schedule:   the schedule to set (dict)
        """
        # Sort calendar day names into the order the robot expects
        days = {}
        for cal_idx, dayname in enumerate(calendar.day_name):
            idx = cal_idx + 1 if cal_idx < 6 else 0
            days[idx] = dayname

        sched = collections.OrderedDict([
            ("cycle", []),
            ("h", []),
            ("m", [])
        ])
        for idx in sorted(days):
            dayname = days[idx]
            if newSchedule[dayname]["clean"]:
                sched["cycle"].append("start")
            else:
                sched["cycle"].append("none")
            sched["h"].append(newSchedule[dayname]["startTime"].hour)
            sched["m"].append(newSchedule[dayname]["startTime"].minute)

        self._PostToRobot("set", ["week", sched])
