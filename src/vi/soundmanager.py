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
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, QLocale, QUrl, QCoreApplication
from .resources import resourcePath
from vi.singleton import Singleton
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtMultimedia import QAudioDevice
from PySide6.QtMultimedia import QMediaDevices

try:
    from espeakng import Speaker
    ESPEAKNG_ENABLED = True
except:
    ESPEAKNG_ENABLED = False
    pass

try:
    from PySide6.QtTextToSpeech import QTextToSpeech
    QTEXTTOSPEECH_ENABLE = True
except Exception as ex:
    QTEXTTOSPEECH_ENABLE = False
    pass

from vi.cache.cache import Cache

global gPygletAvailable

try:
    import pyglet
    from pyglet import media
    gPygletAvailable = True
except ImportError:
    gPygletAvailable = False

# todo:warn sound not match to alarm system distance


class SoundManager(metaclass=Singleton):
    DEF_SND_FILE = "178032__zimbot__redalert-klaxon-sttos-recreated.wav"
    SOUNDS = {"alarm":  DEF_SND_FILE,
              "alarm_0": DEF_SND_FILE,
              "alarm_1": DEF_SND_FILE,
              "alarm_2": DEF_SND_FILE,
              "alarm_3": DEF_SND_FILE,
              "alarm_4": DEF_SND_FILE,
              "alarm_5": DEF_SND_FILE,
              "kos": "178031__zimbot__transporterstartbeep0-sttos-recreated.wav",
              "request": "178028__zimbot__bosun-whistle-sttos-recreated.wav"}

    SNDVOL = {"alarm": 1.00,
              "alarm_0": 0.50,
              "alarm_1": 0.25,
              "alarm_2": 0.125,
              "alarm_3": 0.0625,
              "alarm_4": 0.03125,
              "alarm_5": 0.015625,
              "kos": 0.03,
              "request": 0.03}

    soundVolume = 25  # Must be an integer between 0 and 100
    soundAvailable = True
    useSpokenNotifications = False

    def __init__(self):
        self.sounds = {}
        self.worker = QThread()
        try:
            if QTEXTTOSPEECH_ENABLE:
                self.speach_engine = QTextToSpeech()
            elif ESPEAKNG_ENABLED:
                self.speach_engine = Speaker()
            else:
                self.speach_engine = None
        except Exception as ex:
            self.speach_engine = None
            logging.error(ex)
        self.soundActive = True
        self.audioDevice = QAudioDevice(QMediaDevices.defaultAudioOutput())
        SoundManager.soundAvailable = self.audioDevice is not None
        device_info = QMediaDevices.audioOutputs()
        logging.info("Using default audio device \'{}\'".format(self.audioDevice.description()))
        for device in device_info:
            logging.info(" Availiable audio device \'{}\'".format(device.description()))

        for itm in self.SOUNDS:
            self.sounds[itm] = QSoundEffect(self.audioDevice)
            self.sounds[itm].setLoopCount(0)

        cache = Cache()
        self.setSoundFile("alarm_1", cache.getFromCache("soundsetting.alarm_1"))
        self.setSoundFile("alarm_2", cache.getFromCache("soundsetting.alarm_2"))
        self.setSoundFile("alarm_3", cache.getFromCache("soundsetting.alarm_3"))
        self.setSoundFile("alarm_4", cache.getFromCache("soundsetting.alarm_4"))
        self.setSoundFile("alarm_5", cache.getFromCache("soundsetting.alarm_5"))
        vol = cache.getFromCache("soundsetting.volume")
        if vol:
            self.setSoundVolume(vol)
        self.loadSoundFiles()
        # self.playSound("request")

    def soundFile(self, mask):
        if mask in self.SOUNDS.keys():
            if SoundManager.DEF_SND_FILE == self.SOUNDS[mask]:
                return ""
            else:
                return self.SOUNDS[mask]
        else:
            return ""

    def setSoundFile(self, mask, filename):
        if mask in self.SOUNDS.keys():
            if filename == "" or filename is None:
                filename = SoundManager.DEF_SND_FILE
            self.SOUNDS[mask] = filename

            if self.SOUNDS[mask]:
                url = QUrl.fromLocalFile(self.SOUNDS[mask])
                self.sounds[mask].setSource(url)
            Cache().putIntoCache("soundsetting.{}".format(mask), filename)
            self.loadSoundFiles()

    def loadSoundFiles(self):
        for itm in self.SOUNDS:
            if self.SOUNDS[itm] and os.path.exists(self.SOUNDS[itm]):
                url = QUrl.fromLocalFile(self.SOUNDS[itm])
            elif self.SOUNDS[itm]:
                url = QUrl.fromLocalFile(resourcePath(os.path.join("vi", "ui", "res", "{0}".format(self.SOUNDS[itm]))))
            else:
                url = None
            if url:
                self.sounds[itm].setSource(url)
                QCoreApplication.processEvents()

    def platformSupportsSpeech(self):
        self.useSpokenNotifications = False
        if self.speach_engine:
            if isinstance(self.speach_engine, Speaker):
                self.speach_engine.voice = 'en'
                self.useSpokenNotifications = True
            elif isinstance(self.speach_engine, QTextToSpeech):
                avail_engines = self.speach_engine.getProperty('voices')
                if len(avail_engines):
                    for eng_name in avail_engines:
                        logging.info("Available sound engine \'{}\'".format(eng_name))
                    self.speach_engine.setLocale(QLocale(QLocale.English))
                    self.useSpokenNotifications = True
                    return self.useSpokenNotifications
        if not self.useSpokenNotifications:
            logging.info(" There is no text to speak engine available, all text to speak function disabled.")
        return self.useSpokenNotifications

    def setUseSpokenNotifications(self, new_value):
        self.useSpokenNotifications = new_value

    def setSoundVolume(self, newValue:int):
        self.soundVolume = max(0, min(100, newValue))
        Cache().putIntoCache("soundsetting.volume", self.soundVolume)

    def playSound(self, name="alarm", message="", abbreviatedMessage=""):
        QCoreApplication.processEvents()

        if SoundManager.soundAvailable and self.soundActive:
            if self.useSpokenNotifications and abbreviatedMessage != "":
                if isinstance(self.speach_engine, Speaker):
                    self.speach_engine.amplitude = self.soundVolume
                    self.speach_engine.say(abbreviatedMessage)
                    QCoreApplication.processEvents()
                    QCoreApplication.processEvents()
                else:
                    self.speach_engine.setProperty('volume', self.soundVolume/100.0)
                    self.speach_engine.say(abbreviatedMessage)
                    QCoreApplication.processEvents()
                    QCoreApplication.processEvents()
            elif name in self.sounds.keys() and self.sounds[name] is not None:
                def_sound_effect = self.sounds[name]
                sound_effect = self.sounds[name]
                if sound_effect.isLoaded() and not sound_effect.isPlaying():
                    sound_effect.setVolume(self.soundVolume / 100 * self.SNDVOL[name])
                    sound_effect.setLoopCount(0)
                    sound_effect.play()
                elif def_sound_effect.isLoaded() and not def_sound_effect.isPlaying():
                    def_sound_effect.setVolume(self.soundVolume / 100 * self.SNDVOL[name])
                    def_sound_effect.setLoopCount(0)
                    def_sound_effect.play()
        QCoreApplication.processEvents()

    def quit(self):
        QApplication.processEvents()

    def wait(self):
        QApplication.processEvents()

