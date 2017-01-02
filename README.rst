========
pyirobot
========

This ia a python module for controlling the iRobot Roomba 980 (and possibly Roomba 960 and Braava Jet, but those are untested)

iRobot does not povide an official API for their robots; I reverse engineered this from the communication between my robot, the
iRobot iOS app, and the Axeda IoT cloud service.  The names of methods and attributes are mapped as closely as possible to the
way the ap presents them.

This module is published to `pypi`_, so you can install it via ``pip install pyirobot``

Usage
=====

Robot Password
''''''''''''''

To use any of the robot functions, you will need to get the password of your robot. ``Robot.GetPassword()`` can help you do this.
Make sure your robot is on the home base and then hold down the home button for 3-4 seconds, until the LEDs illuminate and the
robot emits a series of tones.  Then quickly call ``Robot.GetPassword`` with the IP address of your robot.

Controlling the Robot
'''''''''''''''''''''

You can start and stop cleaning and send the robot back to the home base with ``StartCleaning``, ``PauseCleaning``,
``ResumeCleaning``, ``EndCleaning`` and ``ReturnHome``

.. code:: python

    from pyirobot import Robot
    robot = Robot("192.168.0.0", "MtccDqXskShX|4jXnTd")
    robot.StartCleaning()
    
    robot.StopCleaning()
    robot.ReturnHome()

Robot Configuration/Status
''''''''''''''''''''''''''

``GetCleaningPreferences`` returns the cleaning preferences for the robot.  CarpetBoost, CleaningPasses, EdgeClean and
FinishWhenBinFull are all enums in the module.

.. code:: python

    import json
    from pyirobot import Robot
    robot = Robot("192.168.0.0", "MtccDqXskShX|4jXnTd")
    print robot.GetCleaningPreferences()
    print json.dumps(robot.GetCleaningPreferences(), sort_keys=True, indent=4)

Output::

    {u'lang': 0, u'cleaningPasses': <CleaningPasses.Two: 1025>, u'name': u'Roomba', u'finishWhenBinFull': <FinishWhenBinFull.Off: 32>, u'carpetBoost': <CarpetBoost.Auto: 0>, u'edgeClean': <EdgeClean.On: 0>, u'timezone': u'America/Chicago'}

    {
        "carpetBoost": "Auto", 
        "cleaningPasses": "Auto", 
        "edgeClean": "On", 
        "finishWhenBinFull": "Off", 
        "lang": 0, 
        "name": "Roomba", 
        "timezone": "America/Chicago"
    }

``GetMission`` returns real time status about the robot, including battery and bin as well as the current cleaning status, if the robot is currently cleaning.

.. code:: python

    print robot.GetMission()

    {u'binStatus': <BinStatus.Normal: (0,)>, u'readyStatus': <ReadyStatus.Ready: 0>, u'robotPosition': {u'theta': -79, u'point': {u'y': -22, u'x': 2}}, u'robotStatus': <RobotStatus.Charging: 'charge'>, u'missionCoveredSquareFootage': 0, u'missionElapsedMinutes': 0, u'batteryPercentage': 100}

.. code:: python

    print json.dumps(robot.GetMission(), sort_keys=True, indent=4)

    {
        "batteryPercentage": 100, 
        "binStatus": "Normal", 
        "missionCoveredSquareFootage": 0, 
        "missionElapsedMinutes": 0, 
        "readyStatus": "Ready", 
        "robotPosition": {
            "point": {
                "x": 2, 
                "y": -22
            }, 
            "theta": -79
        }, 
        "robotStatus": "Charging"
    }

There are other functions for getting the cleaning schedule, robot time, and various other settings, as well as the corresponding
Set functions, and enums for the various fields.

.. code:: python

    print robot.GetSchedule()

    {'Sunday': {'startTime': datetime.time(9, 0), 'clean': False}, 'Monday': {'startTime': datetime.time(10, 0), 'clean': True}, 'Tuesday': {'startTime': datetime.time(10, 0), 'clean': True}, 'Wednesday': {'startTime': datetime.time(10, 0), 'clean': True}, 'Thursday': {'startTime': datetime.time(10, 0), 'clean': True}, 'Friday': {'startTime': datetime.time(10, 0), 'clean': True}, 'Saturday': {'startTime': datetime.time(10, 0), 'clean': False}}

.. code:: python

    print json.dumps(robot.GetSchedule(), indent=4)

    {
        "Sunday": {
            "startTime": "09:00:00", 
            "clean": false
        }, 
        "Monday": {
            "startTime": "10:00:00", 
            "clean": true
        }, 
        "Tuesday": {
            "startTime": "10:00:00", 
            "clean": true
        }, 
        "Wednesday": {
            "startTime": "10:00:00", 
            "clean": true
        }, 
        "Thursday": {
            "startTime": "10:00:00", 
            "clean": true
        }, 
        "Friday": {
            "startTime": "10:00:00", 
            "clean": true
        }, 
        "Saturday": {
            "startTime": "10:00:00", 
            "clean": false
        }
    }

Errors
''''''

Any error coming back from the robot's API is thrown as a ``RobotError``.  Errors from networking/communication with the robot
are thrown by ``requests`` and uncaught/unmodified by this library.

Known Issues
============
This module is still a work in progress, so error handling and unit tests are pretty light and the API isn't complete yet
This first release only supports local communication with the robot; remote/cloud support is in progress

.. _pypi: https://pypi.python.org/pypi/pyirobot
