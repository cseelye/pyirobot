#!/usr/bin/env python
#pylint: skip-file

from __future__ import print_function
import itertools
import pytest
import types
from .util import RandomComplexString, RandomIP

class Test_PreferenceFlags(object):

    def test_DecodeFlags(self):
        print()

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
        combinations = list(itertools.product(list(CarpetBoost)[1:], list(CleaningPasses)[1:], list(FinishWhenBinFull)[1:], list(EdgeClean)[1:]))
        for combo in combinations:
            setattr(robot, "_fake_preferences", combo)
            print("combo={}".format(combo))
            prefs = robot.GetCleaningPreferences()
            print("prefs={}".format(prefs))
            assert prefs["carpetBoost"] == combo[0]
            assert prefs["cleaningPasses"] == combo[1]
            assert prefs["finishWhenBinFull"] == combo[2]
            assert prefs["edgeClean"] == combo[3]

