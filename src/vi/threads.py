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

import time
import logging
import queue
import os
from PySide6.QtCore import QThread, QRunnable, QThreadPool
from PySide6.QtCore import Signal as pyqtSignal
from vi import evegate
from .cache.cache import Cache
from .resources import resourcePath

STATISTICS_UPDATE_INTERVAL_MSECS = 1 * 60 * 1000


class AvatarFindThread(QThread):

    avatar_update = pyqtSignal(object, object)

    def __init__(self):
        QThread.__init__(self)
        self.queue = queue.Queue()
        self.active = True

    def addChatEntry(self, chat_entry, clear_cache=False):
        try:
            if clear_cache:
                cache = Cache()
                cache.removeAvatar(chat_entry.message.user)

            # Enqeue the data to be picked up in run()
            self.queue.put(chat_entry)
        except Exception as e:
            logging.error("Error in AvatarFindThread: %s", e)

    def run(self):
        last_call = 0
        wait = 500  # time between 2 requests in ms
        while True:
            try:
                # Block waiting for addChatEntry() to enqueue something
                chat_entry = self.queue.get()
                if not self.active:
                    return
                user = chat_entry.message.user

                logging.debug("AvatarFindThread getting avatar for %s" % user)
                avatar = None

                if avatar is None and user == "SPYGLASS":
                    with open(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")), "rb") as f:
                        avatar = f.read()

                if avatar is None:
                    avatar = Cache().getImageFromAvatar(user)
                    if avatar:
                        logging.debug("AvatarFindThread found cached avatar for %s" % user)

                if avatar is None:
                    diff_last_call = time.time() - last_call
                    if diff_last_call < wait:
                        time.sleep((wait - diff_last_call) / 1000.0)
                    evegate.esiCharactersPublicInfo(user)
                    avatar = evegate.esiCharactersPortrait(user)
                    last_call = time.time()
                    if avatar is None:
                        Cache().removeAvatar(user)
                    else:
                        Cache().putImageToAvatar(user, avatar)
                if avatar:
                    logging.debug("AvatarFindThread emit avatar_update for %s" % user)
                    self.avatar_update.emit(chat_entry, avatar)
                else:
                    logging.warning("AvatarFindThread unable to find avatar for %s" % user)
            except Exception as e:
                logging.error("Error in AvatarFindThread : %s", e)

    def quit(self):
        self.active = False
        self.queue.put(None)
        QThread.quit(self)


class FetchSovereignty(QRunnable):

    def __init__(self, notifier):
        QRunnable.__init__(self)
        self.notifier_signal = notifier

    def run(self):
        statistics_data = dict({"result": "pending"})
        try:
            statistics_data["sovereignty"] = evegate.getPlayerSovereignty(fore_refresh=True, show_npc=True)
            statistics_data["structures"] = evegate.esiSovereigntyStructures()
            logging.info("Sovereignty data updated succeeded.")
            statistics_data["result"] = "ok"
        except Exception as e:
            logging.error("Unable to fetch sovereignty update: %s", e)
            statistics_data["result"] = "error"
            statistics_data["text"] = str(e)
        self.notifier_signal.emit(statistics_data)


class FetchStatistic(QRunnable):
    def __init__(self, notifier):
        QRunnable.__init__(self)
        self.notifier_signal = notifier

    def run(self):
        statistics_data = dict({"result": "pending"})
        try:
            statistics_data["statistics"] = evegate.esiUniverseSystem_jumps(use_outdated=False)
            statistics_data["incursions"] = evegate.esiIncursions(use_outdated=False)
            statistics_data["campaigns"] = evegate.getCampaignsSystemsIds(use_outdated=False)
            statistics_data["result"] = "ok"
            logging.info("Statistic data updated succeeded.")
        except Exception as e:
            logging.error("Unable to fetch statistic update: %s", e)
            statistics_data["result"] = "error"
            statistics_data["text"] = str(e)
        self.notifier_signal.emit(statistics_data)


class FetchWormholes(QRunnable):
    def __init__(self, notifier):
        QRunnable.__init__(self)
        self.notifier_signal = notifier




class FetchLocation(QRunnable):
    def __init__(self, notifier):
        QRunnable.__init__(self)
        self.notifier_signal = notifier

    def run(self):
        statistics_data = dict({"result": "pending"})
        try:
            statistics_data["registered-chars"] = evegate.esiGetCharsOnlineStatus()
            logging.info("Fetching the characters location succeeded.")
            statistics_data["result"] = "ok"
        except Exception as e:
            logging.error("Fetching the characters location failed: %s", e)
            statistics_data["result"] = "error"
            statistics_data["text"] = str(e)
        self.notifier_signal.emit(statistics_data)


class MapStatisticsThread(QThread):
    """
    Fetching statistic data and player locations
    """
    statistic_data_update = pyqtSignal(dict)

    def __init__(self):
        QThread.__init__(self)
        self.queue = queue.Queue(maxsize=10)
        self.active = True
        self._fetchLocations = True
        self.queue.put(["sovereignty", "statistics", "location",
                        "thera_wormholes_version"])

    def requestSovereignty(self):
        self.queue.put(["sovereignty"])

    def requestStatistics(self):
        self.queue.put(["statistics"])

    def requestLocations(self):
        if self._fetchLocations:
            self.queue.put(["registered-chars"])

    def requestWormholes(self):
        self.queue.put(["thera_wormholes"])

    def fetchLocation(self, fetch=True):
        self._fetchLocations = fetch

    def run(self):
        while self.active:
            tsk = self.queue.get()
            if not self.active:
                return
            statistics_data = dict({"result": "pending"})
            try:
                if "sovereignty" in tsk:
                    statistics_data["sovereignty"] = evegate.getPlayerSovereignty(fore_refresh=False, show_npc=True)
                    statistics_data["structures"] = evegate.esiSovereigntyStructures()

                if "statistics" in tsk:
                    statistics_data["statistics"] = evegate.esiUniverseSystem_jumps()
                    statistics_data["incursions"] = evegate.esiIncursions(False)
                    statistics_data["campaigns"] = evegate.getCampaignsSystemsIds(False)
                    statistics_data["server-status"] = evegate.esiStatus()

                if "registered-chars" in tsk:
                    statistics_data["registered-chars"] = evegate.esiGetCharsOnlineStatus()

                if "thera_wormholes" in tsk:
                    statistics_data["thera_wormhole"] = evegate.ESAPIListPublicSignatures()

                if "thera_wormholes_version" in tsk:
                    res = evegate.ESAPIHealth()
                    if res:
                        statistics_data["thera_wormholes_version"] = res
                        self.queue.put(["thera_wormholes"])
                    else:
                        self.queue.put( ["thera_wormholes_version"])

                logging.debug("MapStatisticsThread fetching {}succeeded.".format(tsk))
                statistics_data["result"] = "ok"
            except Exception as e:
                logging.error("Error in MapStatisticsThread: %s %s", e, str(tsk))
                statistics_data["result"] = "error"
                statistics_data["text"] = str(e)

            self.statistic_data_update.emit(statistics_data)


    def quit(self):
        self.active = False
        self.queue.put(None)
        QThread.quit(self)
