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
from PyQt5.QtCore import QThread, QLocale
from .resources import resourcePath
from vi.singleton import Singleton
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtTextToSpeech import QTextToSpeech, QVoice
from PyQt5.QtWidgets import qApp
from PyQt5.QtCore import *
from vi.cache.cache import Cache
global gPygletAvailable

try:
    import pyglet
    from pyglet import media
    gPygletAvailable = True
except ImportError:
    gPygletAvailable = False

#todo:warn sound not match to alarm system distance

class SoundManager(metaclass=Singleton):
    SOUNDS = {"alarm": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "alarm_0": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "alarm_1": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "alarm_2": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "alarm_3": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "alarm_4": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "alarm_5": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "kos": "178031__zimbot__transporterstartbeep0-sttos-recreated.wav",
              "request": "178028__zimbot__bosun-whistle-sttos-recreated.wav"}

    SNDVOL = {"alarm": 1.00,
              "alarm_0": 0.50,
              "alarm_1": 0.25,
              "alarm_2": 0.125,
              "alarm_3": 0.07,
              "alarm_4": 0.03,
              "alarm_5": 0.015,
              "kos": 0.30,
              "request": 0.30}

    soundVolume = 25  # Must be an integer between 0 and 100
    soundAvailable = True
    useSpokenNotifications = False
    def __init__(self):
        self.sounds = {}
        self.worker = QThread()
        self.speach_engine = QTextToSpeech()
        cache = Cache()
        self.setSoundFile("alarm_1", cache.getFromCache("soundsetting.alarm_1"))
        self.setSoundFile("alarm_2", cache.getFromCache("soundsetting.alarm_2"))
        self.setSoundFile("alarm_3", cache.getFromCache("soundsetting.alarm_3"))
        self.setSoundFile("alarm_4", cache.getFromCache("soundsetting.alarm_4"))
        self.setSoundFile("alarm_5", cache.getFromCache("soundsetting.alarm_5"))
        vol = cache.getFromCache("soundsetting.volume")
        if vol:
            self.setSoundVolume(float(vol))
        self.loadSoundFiles()

    def soundFile(self, mask):
        if mask in self.SOUNDS.keys():
            return self.SOUNDS[mask]
        else:
            return ""

    def setSoundFile(self,mask,filename):
        if mask in self.SOUNDS.keys():
            if filename is "":
                filename="178032__zimbot__redalert-klaxon-sttos-recreated.wav"
            self.SOUNDS[mask] = filename
            self.sounds[mask] = QSoundEffect()
            url = QUrl.fromLocalFile(self.SOUNDS[mask])
            self.sounds[mask].setSource(url)
            Cache().putIntoCache("soundsetting.{}".format(mask),filename)
            self.loadSoundFiles()

    def loadSoundFiles(self):
        for itm in self.SOUNDS:
            self.sounds[itm] = QSoundEffect()
            if self.SOUNDS[itm]!=None and os.path.exists(self.SOUNDS[itm]):
                url = QUrl.fromLocalFile(self.SOUNDS[itm])
            elif self.SOUNDS[itm]!=None:
                url = QUrl.fromLocalFile(resourcePath(os.path.join("vi", "ui", "res", "{0}".format(self.SOUNDS[itm]))))
            else:
                url = None
            if url!=None:
                self.sounds[itm].setSource(url)


    def platformSupportsAudio(self):
        return True

    def platformSupportsSpeech(self):
        avail_engines = self.speach_engine.availableEngines()
        self.speach_engine.setLocale(QLocale(QLocale.English))
        return len(avail_engines)

    def setUseSpokenNotifications(self, newValue):
        if newValue is not None:
            self.useSpokenNotifications = newValue

    def setSoundVolume(self, newValue):
        self.soundVolume = max(0.0, min(100.0, newValue))
        Cache().putIntoCache("soundsetting.volume", self.soundVolume)
        for itm in self.sounds.keys():
            self.sounds[itm].setVolume(self.soundVolume/100)

    def playSound(self, name="alarm", message="", abbreviatedMessage=""):
        if self.soundAvailable and self.soundActive:
            if self.useSpokenNotifications and abbreviatedMessage != "":
                self.speach_engine.setVolume(self.soundVolume/100.0)
                self.speach_engine.say(abbreviatedMessage)
            elif name in self.sounds.keys():
                self.sounds[name].setVolume(self.soundVolume / 100. * self.SNDVOL[name])
                self.sounds[name].setMuted(False)
                self.sounds[name].play()
                self.sounds[name].status()
            else:
                self.sounds[name].setVolume(self.soundVolume / 100.0 * self.SNDVOL[name])
                self.sounds["alarm"].setMuted(False)
                self.sounds["alarm"].play()
                self.sounds["alarm"].status()
        qApp.processEvents()

    def quit(self):
        qApp.processEvents()

    def wait(self):
        qApp.processEvents()

