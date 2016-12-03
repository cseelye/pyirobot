========
pyirobot
========

This ia a python module for controlling the iRobot Roomba 980 (and possibly Roomba 960 and Braava 300, but those are untested)

iRobot does not povide an official API for their robots; I reverse engineered this from the communication between my robot, the
iRobot iOS app, and the Axeda IoT cloud service.

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

Robot Configuration
'''''''''''''''''''
``GetPreferences`` returns the cleaning preferences for the robot.  CarpetBoost, CleaningPasses, EdgeClean and FinishWhenBinFull
are all enums in the module.

.. code:: python

    import json
    from pyirobot import Robot
    robot = Robot("192.168.0.0", "MtccDqXskShX|4jXnTd")
    print json.dumps(robot.GetPreferences(), sort_keys=True, indent=4)

Output::

    {
        "carpetBoost": "Auto", 
        "cleaningPasses": "Auto", 
        "edgeClean": "On", 
        "finishWhenBinFull": "Off", 
        "lang": 0, 
        "name": "Roomba", 
        "timezone": "America/Chicago"
    }

There are other functions for getting the cleaning schedule, robot time, and various other settings, as well as the corresponding
Set functions.

Known Issues
============
This module is still a work in progress, so error handling and unit tests are pretty light and the API isn't complete yet
This first release only supports local communication with the robot; remote/cloud support is in progress
