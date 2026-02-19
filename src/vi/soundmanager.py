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
import shutil
import subprocess
from typing import Dict, Optional

from threading import Thread
from PySide6.QtCore import QLocale, QUrl, QCoreApplication
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
from vi.resources import resourcePath
from vi.singleton import Singleton
from vi.cache.cache import Cache


try:
    from PySide6.QtTextToSpeech import QTextToSpeech
    QT_TEXT_TO_SPEECH_ENABLED = True
except (Exception,):
    QT_TEXT_TO_SPEECH_ENABLED = False

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


class BaseSoundBackend:
    """Interface for sound playback backends.

    Attributes:
        name: Identifier for the backend implementation.
        available: True when the backend can play audio.
    """
    name = "base"

    def __init__(self):
        """Mark the backend as unavailable until configured."""
        self.available = False

    def prepare(self, key: str, filename: Optional[str]) -> None:
        """Register or preload the sound for a key.

        Args:
            key: Logical sound identifier.
            filename: Path to a WAV file or None to clear the mapping.
        """
        raise NotImplementedError

    def play(self, key: str, volume: float) -> bool:
        """Play a registered sound.

        Args:
            key: Logical sound identifier.
            volume: Linear volume from 0.0 to 1.0 after master gain.

        Returns:
            True when playback was triggered, otherwise False.
        """
        raise NotImplementedError

    def set_master_volume(self, volume: float) -> None:
        """Set master volume applied to all sounds.

        Args:
            volume: Linear gain between 0.0 and 1.0.
        """
        raise NotImplementedError

    def stop_all(self) -> None:
        """Stop all currently playing sounds."""
        raise NotImplementedError


class QtSoundBackend(BaseSoundBackend):
    """Qt6-based sound playback using QSoundEffect.

    Attributes:
        audio_device: Optional QAudioDevice to route playback.
        effects: Map of keys to QSoundEffect instances.
    """
    name = "qt6"

    def __init__(self, audio_device=None):
        """Create a Qt-based backend.

        Args:
            audio_device: Optional target audio device.
        """
        super().__init__()
        self.audio_device = audio_device
        self.effects: Dict[str, Optional[QSoundEffect]] = {}
        self.available = True

    def prepare(self, key: str, filename: Optional[str]) -> None:
        """Create and store a QSoundEffect for a key."""
        if filename is None:
            self.effects[key] = None
            return
        effect = QSoundEffect()
        if self.audio_device:
            effect.setAudioDevice(self.audio_device)
        effect.setSource(QUrl.fromLocalFile(filename))
        effect.setLoopCount(1)
        QCoreApplication.processEvents()
        if effect.status() == QSoundEffect.Status.Ready:
            self.effects[key] = effect

    def play(self, key: str, volume: float) -> bool:
        """Play a sound via QSoundEffect with the given volume."""
        effect = self.effects.get(key)
        if not effect:
            return False
        if effect.status() == QSoundEffect.Status.Error:
            logging.warning(
                "Qt sound backend failed to load sound '%s': %s",
                key,
                effect.source().toString(),
            )
            return False
        if effect.isPlaying():
            effect.stop()
        if effect.status() == QSoundEffect.Status.Ready:
            effect.setVolume(volume)
        else:
            return False
        if effect.status() == QSoundEffect.Status.Ready:
            effect.play()
        else:
            return False
        return True

    def set_master_volume(self, volume: float) -> None:
        """Update cached effect volumes for immediate playback."""
        # Volume is applied per play call; update cached effects for immediate use.
        for effect in self.effects.values():
            if effect:
                effect.setVolume(volume)

    def stop_all(self) -> None:
        """Stop all QSoundEffect instances."""
        for effect in self.effects.values():
            if effect:
                effect.stop()


class ExternalProcessBackend(BaseSoundBackend):
    """Linux-friendly backend using system audio tools (paplay/aplay).

    Attributes:
        _command: Selected external audio command.
        _supports_volume: True when the command supports volume flags.
        _master_volume: Master gain applied to the backend.
        paths: Map of keys to sound file paths.
    """
    name = "external"

    def __init__(self):
        """Select an external audio command available on the system."""
        super().__init__()
        self._command = None
        self._supports_volume = False
        self._master_volume = 1.0
        self.paths: Dict[str, Optional[str]] = {}
        if shutil.which("paplay"):
            self._command = "paplay"
            self._supports_volume = True
        elif shutil.which("aplay"):
            self._command = "aplay"
        if self._command:
            self.available = True

    def prepare(self, key: str, filename: Optional[str]) -> None:
        """Store the path for later playback."""
        if filename and os.path.exists(filename):
            self.paths[key] = filename
        else:
            self.paths[key] = None

    def play(self, key: str, volume: float) -> bool:
        """Spawn the external process to play a WAV file."""
        if not self.available or volume <= 0.0 or self._master_volume <= 0.0:
            return False
        path = self.paths.get(key)
        if not path:
            return False
        try:
            cmd = [self._command]
            if self._command == "paplay" and self._supports_volume:
                vol_value = int(max(0.0, min(1.0, volume)) * 65536)
                cmd.append(f"--volume={vol_value}")
            elif self._command == "aplay":
                cmd.append("-q")
            cmd.append(path)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as ex:
            logging.error(ex)
            return False

    def set_master_volume(self, volume: float) -> None:
        """Store master gain used when the backend supports volume."""
        self._master_volume = max(0.0, min(1.0, volume))

    def stop_all(self) -> None:
        """External processes are fire-and-forget; nothing to stop here."""
        return


class NullSoundBackend(BaseSoundBackend):
    """No-op backend to keep the API consistent when sound is unavailable."""
    name = "none"

    def __init__(self):
        """Initialize the backend as unavailable."""
        super().__init__()
        self.available = False

    def prepare(self, key: str, filename: Optional[str]) -> None:
        """Ignore sound registration for the null backend."""
        return

    def play(self, key: str, volume: float) -> bool:
        """Ignore playback requests for the null backend."""
        return False

    def set_master_volume(self, volume: float) -> None:
        """Ignore volume updates for the null backend."""
        return

    def stop_all(self) -> None:
        """Ignore stop requests for the null backend."""
        return


class SoundPlayer:
    """Coordinator that can switch between different playback backends.

    Attributes:
        _master_volume: Global gain applied to all sounds.
        _backends: Available backend instances keyed by name.
        _backend: Active backend instance.
    """
    def __init__(self, audio_device=None, enable_qt_backend: bool = True):
        """Build the sound player and initialize available backends.

        Args:
            audio_device: Optional Qt audio device to use when available.
            enable_qt_backend: Disable to skip Qt backend registration.
        """
        self._master_volume = 0.5
        self._backends: Dict[str, BaseSoundBackend] = {}
        self._backend: BaseSoundBackend = NullSoundBackend()
        self._init_backends(audio_device, enable_qt_backend)

    def _init_backends(self, audio_device, enable_qt_backend: bool) -> None:
        """Initialize available backends, preferring Qt when present."""
        if enable_qt_backend:
            qt_backend = QtSoundBackend(audio_device=audio_device)
            self._backends[qt_backend.name] = qt_backend
        external_backend = ExternalProcessBackend()
        if external_backend.available:
            self._backends[external_backend.name] = external_backend
        if self._backends:
            # Prefer Qt when present.
            preferred = ExternalProcessBackend.name if ExternalProcessBackend.name in self._backends else list(self._backends.keys())[0]
            self._backend = self._backends[preferred]

    @property
    def available(self) -> bool:
        """Return True when the active backend can play sounds."""
        return self._backend.available

    @property
    def backend_name(self) -> str:
        """Return the name of the active backend."""
        return self._backend.name

    @property
    def backend(self) -> BaseSoundBackend:
        """Expose the active backend instance."""
        return self._backend

    def set_backend(self, name: str) -> bool:
        """Select a backend by name if it is available.

        Args:
            name: Backend identifier (e.g., 'qt6', 'external').

        Returns:
            True when the backend was switched, otherwise False.
        """
        backend = self._backends.get(name)
        if backend and backend.available:
            self._backend = backend
            backend.set_master_volume(self._master_volume)
            return True
        return False

    def register_sound(self, key: str, filename: Optional[str]) -> None:
        """Register a sound file with all available backends.

        Args:
            key: Logical sound identifier.
            filename: Path to WAV file or None to clear.
        """
        for backend in self._backends.values():
            if backend.available:
                backend.prepare(key, filename)

    def set_master_volume(self, volume: float) -> None:
        """Update master volume and propagate to backend.

        Args:
            volume: Linear gain between 0.0 and 1.0.
        """
        self._master_volume = max(0.0, min(1.0, volume))
        for backend in self._backends.values():
            if backend.available:
                backend.set_master_volume(self._master_volume)

    def play(self, key: str, relative_volume: float) -> None:
        """Play a registered sound with per-sound gain.

        Args:
            key: Logical sound identifier.
            relative_volume: Sound-specific gain 0.0-1.0.
        """
        if not self.available:
            return
        final_volume = max(0.0, min(1.0, self._master_volume * relative_volume))
        if final_volume <= 0.0:
            return
        if self._backend.play(key, final_volume):
            return
        # Fallback from Qt to external player when Qt reports a failure.
        if self._backend.name == "qt6":
            fallback = self._backends.get("external")
            if fallback and fallback.available and fallback.play(key, final_volume):
                self._backend = fallback
                logging.info("Switched sound backend to 'external' after Qt playback failure.")

    def stop_all(self) -> None:
        """Stop any ongoing playback."""
        for backend in self._backends.values():
            if backend.available:
                backend.stop_all()


class SayThread(Thread):
    """Threaded text-to-speech runner using pyttsx3."""
    soundVolume = 100.0

    def __init__(self, *args, **kwargs):
        """Spawn a thread to perform text-to-speech playback."""
        Thread.__init__(self, *args, **kwargs)
        self.daemon = True
        self.start()

    def run(self):
        """Execute queued speech using the selected pyttsx3 engine."""
        tts_engine = pyttsx3.init("sapi5" if sys.platform.startswith("win32") else "espeak-ng")
        tts_engine.setProperty('volume', self.soundVolume)
        tts_engine.say(self._args)
        tts_engine.runAndWait()


class SoundManager(metaclass=Singleton):
    """Manage sound configuration, playback, and TTS integration.

    Attributes:
        DEF_SND_FILE: Default WAV file used when none is configured.
        SOUNDS: Map of sound keys to filenames.
        SNDVOL: Per-sound gain multipliers.
        EFFECT: Legacy cache for QSoundEffect references.
        soundVolume: Master volume 0-100.
        soundAvailable: True when any backend is available.
        useSpokenNotifications: Enable speech notifications when supported.
    """
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

    SNDVOL = {"alarm": 0.8,
              "alarm_0": 0.7,
              "alarm_1": 0.6,
              "alarm_2": 0.5,
              "alarm_3": 0.4,
              "alarm_4": 0.3,
              "alarm_5": 0.20,
              "kos": 0.3,
              "request": 0.3}

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
        """Initialize sound backends, devices, cache, and TTS engines."""
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
            elif QT_TEXT_TO_SPEECH_ENABLED:
                self.speach_engine = QTextToSpeech()
                self.speach_engine.setLocale(QLocale('en-US'))
            else:
                self.speach_engine = None
        except (Exception,) as ex:
            self.speach_engine = None
            logging.error(ex)
        self._audio_device = None
        qt_outputs = list()
        try:
            qt_outputs = list(QMediaDevices.audioOutputs())
            self.audioDevices = tuple(device.description() for device in qt_outputs)
            if qt_outputs:
                self._audio_device = QMediaDevices.defaultAudioOutput()
                logging.info("Using Qt6 audio device '{}'".format(self._audio_device.description()))
        except Exception as ex:
            logging.error(ex)
            self.audioDevices = tuple()

        # Keep Qt backend enabled even when device enumeration is empty; some systems
        # still route to a default output, and we can fallback to external when needed.
        self._player = SoundPlayer(audio_device=self._audio_device, enable_qt_backend=True)
        self.soundAvailable = self._player.available
        type(self).soundAvailable = self.soundAvailable
        self.soundActive = self.soundAvailable
        if self.soundAvailable:
            if self._player.backend_name == "qt6":
                default_name = self._audio_device.description() if self._audio_device else "default"
                logging.info("Using Qt6 audio device '{}'".format(default_name))
                for device in qt_outputs:
                    if self._audio_device and device == self._audio_device:
                        continue
                    logging.info(" Available audio device '{}'".format(device.description()))
                if not qt_outputs:
                    logging.info(" Qt returned no enumerated outputs; using default routing.")
            else:
                logging.info("Using external audio backend '{}'".format(self._player.backend_name))
        else:
            logging.warning("No audio output devices found or external player missing. Sound is disabled.")

        cache = Cache()
        self.SOUNDS["alarm_1"] = cache.getFromCache("soundsetting.alarm_1")
        self.SOUNDS["alarm_2"] = cache.getFromCache("soundsetting.alarm_2")
        self.SOUNDS["alarm_3"] = cache.getFromCache("soundsetting.alarm_3")
        self.SOUNDS["alarm_4"] = cache.getFromCache("soundsetting.alarm_4")
        self.SOUNDS["alarm_5"] = cache.getFromCache("soundsetting.alarm_5")
        vol = cache.getFromCache("soundsetting.volume")
        if vol is not None:
            try:
                self.soundVolume = int(vol)
            except (TypeError, ValueError):
                logging.warning("Invalid cached sound volume '{}'; using default.".format(vol))
        self.soundVolume = max(0, min(100, int(self.soundVolume)))
        if self._player:
            self._player.set_master_volume(self.soundVolume / 100.0)
        self.loadSoundFiles()

    def soundFile(self, mask):
        """Return the configured sound filename for a key.

        Args:
            mask: Logical sound identifier.

        Returns:
            The filename or empty string when default/absent.
        """
        if mask in self.SOUNDS.keys():
            if self.DEF_SND_FILE == self.SOUNDS[mask]:
                return ""
            else:
                return self.SOUNDS[mask]
        else:
            return ""

    def setSoundFile(self, mask, filename):
        """Override the sound file for a specific key.

        Args:
            mask: Logical sound identifier.
            filename: Path to WAV file; default used when empty/None.
        """
        if mask in self.SOUNDS.keys():
            if filename == "" or filename is None:
                filename = self.DEF_SND_FILE
            self.SOUNDS[mask] = filename
            Cache().putIntoCache("soundsetting.{}".format(mask), filename)
            self.loadSoundFile(mask)

    def _resolve_sound_file(self, sound_filename: Optional[str]) -> Optional[str]:
        """Resolve a configured sound filename to an existing path.

        Resolution order:
            1) Absolute path (or user-expanded path).
            2) Path relative to current working directory.
            3) Legacy resourcePath lookup.
            4) Path relative to this package (`vi/ui/res`).

        Args:
            sound_filename: Configured filename or path.

        Returns:
            Existing absolute/relative path, or None if unresolved.
        """
        if not sound_filename:
            return None
        expanded = os.path.expanduser(str(sound_filename))
        candidates = [expanded]
        if not os.path.isabs(expanded):
            candidates.append(resourcePath(os.path.join("vi", "ui", "res", expanded)))
            candidates.append(os.path.join(os.path.dirname(__file__), "ui", "res", expanded))
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def loadSoundFile(self, itm):
        """Load and register a single sound file with the active backend.

        Args:
            itm: Logical sound identifier.
        """
        sound_filename = self.SOUNDS[itm]
        if sound_filename is None:
            self.SOUNDS[itm] = SoundManager.DEF_SND_FILE
            sound_filename = SoundManager.DEF_SND_FILE
        sound_filename_used = self._resolve_sound_file(sound_filename)
        if sound_filename and sound_filename_used is None:
            logging.warning("Sound file for '{}' not found: '{}'".format(itm, sound_filename))

        if self._player.available:
            self._player.register_sound(itm, sound_filename_used)
            # Keep the legacy map populated when the Qt backend is active.
            if isinstance(self._player.backend, QtSoundBackend):
                self.EFFECT[itm] = self._player.backend.effects.get(itm)
            else:
                self.EFFECT[itm] = None

    def loadSoundFiles(self):
        """Load all configured sounds into the active backend."""
        if not self.soundAvailable:
            for itm in self.SOUNDS:
                self.EFFECT[itm] = None
            return
        for itm in self.SOUNDS:
            self.loadSoundFile(itm)

    def platformSupportsSpeech(self):
        """Check if TTS is available and set up for notifications."""
        self.useSpokenNotifications = False
        if self.speach_engine:
            if isinstance(self.speach_engine, QTextToSpeech):
                self.useSpokenNotifications = True
            elif PYTTSX3_ENABLED and isinstance(self.speach_engine, pyttsx3.engine.Engine):
                self.useSpokenNotifications = True
            elif isinstance(self.speach_engine, Speaker):
                self.speach_engine.voice = 'en'
                self.useSpokenNotifications = True
            return self.useSpokenNotifications
        if not self.useSpokenNotifications:
            logging.info(" There is no text to speak engine available, all text to speak function disabled.")
        return self.useSpokenNotifications

    def setUseSpokenNotifications(self, new_value):
        """Enable or disable spoken notifications."""
        self.useSpokenNotifications = new_value

    def setSoundVolume(self, new_value: int):
        """Set master volume and propagate to the backend.

        Args:
            new_value: Desired volume 0-100.
        """
        self.soundVolume = max(0, min(100, new_value))
        Cache().putIntoCache("soundsetting.volume", self.soundVolume)
        if self._player:
            self._player.set_master_volume(self.soundVolume / 100.0)

    def playSound(self, name="alarm", message="", abbreviated_message=""):
        """Play a sound or speak a message based on current settings.

        Args:
            name: Logical sound identifier.
            message: Unused legacy message text.
            abbreviated_message: Text to speak when TTS is enabled.
        """
        if self.soundAvailable and self.soundActive:
            if self.useSpokenNotifications and abbreviated_message != "":
                if isinstance(self.speach_engine, QTextToSpeech):
                    self.speach_engine.say(abbreviated_message)
                elif PYTTSX3_ENABLED and isinstance(self.speach_engine, pyttsx3.engine.Engine):
                    SayThread.soundVolume = self.soundVolume / 100.0
                    SayThread(args=abbreviated_message)

                elif isinstance(self.speach_engine, Speaker):
                    self.speach_engine.amplitude = self.soundVolume
                    self.speach_engine.say(abbreviated_message)
                else:
                    self.speach_engine.setProperty('volume', self.soundVolume/100.0)
                    self.speach_engine.say(abbreviated_message)
            elif name in self.SNDVOL.keys():
                self._player.play(name, self.SNDVOL[name])

    def quit(self):
        """Stop all ongoing playback."""
        if self._player:
            self._player.stop_all()

    def wait(self):
        """Stop all ongoing playback (alias for quit)."""
        if self._player:
            self._player.stop_all()
