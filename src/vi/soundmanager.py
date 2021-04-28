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
global gPygletAvailable

try:
    import pyglet
    from pyglet import media
    gPygletAvailable = True
except ImportError:
    gPygletAvailable = False


class SoundManager(metaclass=Singleton):
    SOUNDS = {"alarm": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
              "alarm_1": "",
              "alarm_2": "",
              "alarm_3": "",
              "alarm_4": "",
              "kos": "178031__zimbot__transporterstartbeep0-sttos-recreated.wav",
              "request": "178028__zimbot__bosun-whistle-sttos-recreated.wav"}

    soundVolume = 25  # Must be an integer between 0 and 100
    soundAvailable = True
    useSpokenNotifications = False
    def __init__(self):
        self.sounds = {}
        self.worker = QThread()
        self.speach_engine = QTextToSpeech()
        #for loc in self.speach_engine.availableLocales():
        #    if loc.language() == Qt.QLocale.ation.english:
        #        self.speach_engine.setLocale( loc )
        for itm in self.SOUNDS:
            self.sounds[itm] = QSoundEffect()
            url = QUrl.fromLocalFile(resourcePath(os.path.join("vi", "ui", "res", "{0}".format(self.SOUNDS[itm]))))
            self.sounds[itm].setSource(url)

    def soundFile(self,mask):
        if mask in self.SOUNDS.keys():
            return self.SOUNDS[mask]
        else:
            return ""

    def setSoundFile(self,mask,filename):
        if mask in self.SOUNDS.keys():
            self.SOUNDS[mask] = filename
            self.sounds[mask] = QSoundEffect()
            url = QUrl.fromLocalFile(self.SOUNDS[mask])
            self.sounds[mask].setSource(url)


    def platformSupportsAudio(self):
        return True

    def platformSupportsSpeech(self):
        avail_engines = self.speach_engine.availableEngines()
        self.speach_engine.setLocale(QLocale(QLocale.English))
        return len(avail_engines)
        #avail_locales = self.speach_engine.availableLocales()
        self.speach_engine.setLocale(QLocale(QLocale.English))
        avail_voices = self.speach_engine.availableVoices()
        #self.speach_engine.setVoice(avail_voices[24])#5
        #self.id_voice = 26
        return len(avail_voices)

    def setUseSpokenNotifications(self, newValue):
        if newValue is not None:
            self.useSpokenNotifications = newValue

    def setSoundVolume(self, newValue):
        self.soundVolume = max(0.0, min(100.0, newValue))
        for itm in self.sounds.keys():
            self.sounds[itm].setVolume(self.soundVolume/100)

    def playSound(self, name="alarm", message="", abbreviatedMessage=""):
        audioFile = None
        if self.soundAvailable and self.soundActive:
            if self.useSpokenNotifications and abbreviatedMessage!="":
                #todo:use QTextToSpeach here
                audioFile = None
                #avail_voices = self.speach_engine.availableVoices()
                #self.speach_engine.setVoice(avail_voices[self.id_voice])  # 5
                #self.id_voice = self.id_voice + 1
                self.speach_engine.say(abbreviatedMessage)
            elif name in self.sounds.keys():
                self.sounds[name].play()
            else:
                self.sounds["alarm"].setMuted(False)
                self.sounds["alarm"].play()
                res = self.sounds["alarm"].status()
        qApp.processEvents()

    def quit(self):
        pass

