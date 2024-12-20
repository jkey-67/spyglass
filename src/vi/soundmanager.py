###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#                                                                         #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import os
import sys
import logging

import pygame
import pygame._sdl2.audio as sdl2_audio

from threading import Thread
from vi.resources import resourcePath
from vi.singleton import Singleton
from vi.cache.cache import Cache


try:
    from PySide6.QtTextToSpeech import QTextToSpeech
    QT_TEXT_TO_SPEECH_ENABLED = True
except (Exception,):
    QT_TEXT_TO_SPEECH_ENABLE = False
    pass

try:
    import pyttsx3
    PYTTSX3_ENABLED = True
except (Exception,):
    PYTTSX3_ENABLED = False
    pass

try:
    from espeakng import Speaker
    ESPEAKNG_ENABLED = True
except (Exception,):
    ESPEAKNG_ENABLED = False
    pass


class SayThread(Thread):
    soundVolume = 100.0

    def __init__(self, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self.daemon = True
        self.start()

    def run(self):
        tts_engine = pyttsx3.init("sapi5" if sys.platform.startswith("win32") else "espeak-ng")
        tts_engine.setProperty('volume', self.soundVolume)
        tts_engine.say(self._args)
        tts_engine.runAndWait()


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

    SNDVOL = {"alarm": 0.75,
              "alarm_0": 0.50,
              "alarm_1": 0.25,
              "alarm_2": 0.125,
              "alarm_3": 0.0625,
              "alarm_4": 0.03125,
              "alarm_5": 0.015625,
              "kos": 0.03,
              "request": 0.03}

    EFFECT = {"alarm": None,
              "alarm_0": None,
              "alarm_1": None,
              "alarm_2": None,
              "alarm_3": None,
              "alarm_4": None,
              "alarm_5": None,
              "kos": None,
              "request": None}
    soundVolume = 50  # Must be an integer between 0 and 100
    soundAvailable = True
    useSpokenNotifications = False

    def __init__(self):
        try:
            if PYTTSX3_ENABLED and sys.platform.startswith("win32"):
                self.speach_engine = pyttsx3.init("sapi5")
                for voice in self.speach_engine.getProperty('voices'):
                    print(voice)
                    if "_EN-US" in voice.id:
                        self.speach_engine.setProperty('voice', voice.id)
                        break
            elif ESPEAKNG_ENABLED:
                self.speach_engine = Speaker()
            else:
                self.speach_engine = None
        except Exception as ex:
            self.speach_engine = None
            logging.error(ex)
        pygame.mixer.init()
        self.audioDevices = tuple(sdl2_audio.get_audio_device_names(False))
        self.soundActive = True
        self.soundAvailable = self.audioDevices is not None
        logging.info("Using default audio device \'{}\'".format(self.audioDevices[0]))
        for device in self.audioDevices[1:]:
            logging.info(" Availiable audio device \'{}\'".format(device))

        cache = Cache()
        self.SOUNDS["alarm_1"] = cache.getFromCache("soundsetting.alarm_1")
        self.SOUNDS["alarm_2"] = cache.getFromCache("soundsetting.alarm_2")
        self.SOUNDS["alarm_3"] = cache.getFromCache("soundsetting.alarm_3")
        self.SOUNDS["alarm_4"] = cache.getFromCache("soundsetting.alarm_4")
        self.SOUNDS["alarm_5"] = cache.getFromCache("soundsetting.alarm_5")
        vol = cache.getFromCache("soundsetting.volume")
        if vol:
            self.soundVolume = vol
        pygame.mixer.init()
        self.loadSoundFiles()

    def soundFile(self, mask):
        if mask in self.SOUNDS.keys():
            if self.DEF_SND_FILE == self.SOUNDS[mask]:
                return ""
            else:
                return self.SOUNDS[mask]
        else:
            return ""

    def setSoundFile(self, mask, filename):
        if mask in self.SOUNDS.keys():
            if filename == "" or filename is None:
                filename = self.DEF_SND_FILE
            self.SOUNDS[mask] = filename
            Cache().putIntoCache("soundsetting.{}".format(mask), filename)
            self.loadSoundFile(mask)

    def loadSoundFile(self, itm):
        sound_filename = self.SOUNDS[itm]
        if sound_filename is None:
            self.SOUNDS[itm] = SoundManager.DEF_SND_FILE
            sound_filename = SoundManager.DEF_SND_FILE
        res_sound_filename = resourcePath(os.path.join("vi", "ui", "res", sound_filename))
        if sound_filename and os.path.exists(sound_filename):
            sound_filename_used = sound_filename
        elif self.SOUNDS[itm] and os.path.exists(res_sound_filename):
            sound_filename_used = res_sound_filename
        else:
            sound_filename_used = None

        if self.EFFECT[itm]:
            self.EFFECT[itm].fadeout(25)
        if sound_filename_used is not None:
            self.EFFECT[itm] = pygame.mixer.Sound(sound_filename_used)
            self.EFFECT[itm].set_volume(self.soundVolume / 100 * self.SNDVOL[itm])
        elif self.EFFECT[itm]:
            self.EFFECT[itm] = None

    def loadSoundFiles(self):
        for itm in self.SOUNDS:
            self.loadSoundFile(itm)

    def platformSupportsSpeech(self):
        self.useSpokenNotifications = False
        if self.speach_engine:
            if isinstance(self.speach_engine, pyttsx3.engine.Engine):
                self.useSpokenNotifications = True
            elif isinstance(self.speach_engine, Speaker):
                self.speach_engine.voice = 'en'
                self.useSpokenNotifications = True
            return self.useSpokenNotifications
        if not self.useSpokenNotifications:
            logging.info(" There is no text to speak engine available, all text to speak function disabled.")
        return self.useSpokenNotifications

    def setUseSpokenNotifications(self, new_value):
        self.useSpokenNotifications = new_value

    def setSoundVolume(self, new_value: int):
        self.soundVolume = max(0, min(100, new_value))
        Cache().putIntoCache("soundsetting.volume", self.soundVolume)
        for key, val in self.EFFECT.items():
            val.set_volume(self.soundVolume / 100 * self.SNDVOL[key])

    def playSound(self, name="alarm", message="", abbreviated_message=""):
        if self.soundAvailable and self.soundActive:
            if self.useSpokenNotifications and abbreviated_message != "":
                if isinstance(self.speach_engine, pyttsx3.engine.Engine):
                    SayThread.soundVolume = self.soundVolume / 100.0
                    SayThread(args=abbreviated_message)

                elif isinstance(self.speach_engine, Speaker):
                    self.speach_engine.amplitude = self.soundVolume
                    self.speach_engine.say(abbreviated_message)
                else:
                    self.speach_engine.setProperty('volume', self.soundVolume/100.0)
                    self.speach_engine.say(abbreviated_message)
            elif name in self.EFFECT.keys() and self.EFFECT[name] is not None:
                self.EFFECT[name].fadeout(125)
                self.EFFECT[name].play()

    def quit(self):
        for effect in self.EFFECT.values():
            if effect:
                effect.fadeout(125)

    def wait(self):
        for effect in self.EFFECT.values():
            if effect:
                effect.stop()
        pygame.mixer.quit()
