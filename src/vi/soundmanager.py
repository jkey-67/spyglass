###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import os
import subprocess
import sys
import re
import requests
import time

from collections import namedtuple
from PyQt5.QtCore import QThread
from .resources import resourcePath
import queue
import logging
from vi.singleton import Singleton
from PyQt5.QtMultimedia import QSoundEffect, QMediaPlayer
from PyQt5.QtWidgets import qApp
from PyQt5.QtCore import QUrl
global gPygletAvailable

try:
    import pyglet
    from pyglet import media
    gPygletAvailable = True
except ImportError:
    gPygletAvailable = False


class SoundManager(metaclass=Singleton):
    SOUNDS = {"alarm": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "kos": "178031__zimbot__transporterstartbeep0-sttos-recreated.wav",
              "request": "178028__zimbot__bosun-whistle-sttos-recreated.wav"}

    soundVolume = 25  # Must be an integer between 0 and 100
    soundAvailable = True
    useSpokenNotifications = False
    def __init__(self):
        self.sounds = {}
        self.worker = QThread()
        for itm in self.SOUNDS:
            self.sounds[itm] = QSoundEffect()
            url = QUrl.fromLocalFile(resourcePath(os.path.join("vi", "ui", "res", "{0}".format(self.SOUNDS[itm]))))
            self.sounds[itm].setSource( url)
            #self.sounds[itm].moveToThread( self.worker )

    def platformSupportsAudio(self):
        return True

    def platformSupportsSpeech(self):
        return False

    def setUseSpokenNotifications(self, newValue):
        if newValue is not None:
            self.useSpokenNotifications = newValue

    def setSoundVolume(self, newValue):
        self.soundVolume = max(0.0, min(100.0, newValue))
        for itm in self.sounds.keys():
            self.sounds[itm].setVolume(self.soundVolume/100)

    def playSound(self, name="alarm", message="", abbreviatedMessage=""):
        if self.soundAvailable and self.soundActive:
            if self.useSpokenNotifications:
                audioFile = None
            elif name in self.sounds.keys():
                self.sounds[name].play()
            else:
                self.sounds["alarm"].setMuted(False)
                self.sounds["alarm"].play()
                res = self.sounds["alarm"].status()
        qApp.processEvents()

    def quit(self):
        pass

