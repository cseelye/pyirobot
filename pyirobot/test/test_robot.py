#!/usr/bin/env python
#pylint: skip-file

import itertools
import pytest
import types
from .util import RandomComplexString, RandomIP

class Test_PreferenceFlags(object):

    def test_DecodeFlags(self, monkeypatch):
        print

        from pyirobot import CarpetBoost, CleaningPasses, FinishWhenBinFull, EdgeClean, Robot
        robot = Robot(RandomIP(), RandomComplexString(64))

        # Fake the robot post call
        def fake_post(self, cmd, args):
            return {
                "lang" : 0,
                "name" : "Roomba",
                "timezone" : "America/Chicago",
                "flags" : sum([field.value for field in self._fake_preferences])
            }
        setattr(robot, "_PostToRobot", types.MethodType(fake_post, robot))

        # Test decoding every combination of options
        combinations = list(itertools.product(list(CarpetBoost), list(CleaningPasses), list(FinishWhenBinFull), list(EdgeClean)))
        for combo in combinations:
            setattr(robot, "_fake_preferences", combo)
            prefs = robot.GetPreferences()
            assert CarpetBoost[prefs["carpetBoost"]] == combo[0]
            assert CleaningPasses[prefs["cleaningPasses"]] == combo[1]
            assert FinishWhenBinFull[prefs["finishWhenBinFull"]] == combo[2]
            assert EdgeClean[prefs["edgeClean"]] == combo[3]

