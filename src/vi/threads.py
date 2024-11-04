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


class MapStatisticsThread(QThread):
    """
    Fetching statistic data and player locations
    """
    statistic_data_update = pyqtSignal(dict)

    def __init__(self):
        QThread.__init__(self)
        self.queue = queue.Queue(maxsize=10)
        self.server_status = False
        self.active = True
        self._fetchLocations = True
        self.queue.put(["server-status", "thera_wormholes_version"])

    def requestSovereignty(self):
        self.queue.put(["sovereignty"])

    def requestStatistics(self):
        if self.server_status:
            self.queue.put(["statistics", "incursions", "campaigns", "sovereignty", "structures"])

    def requestLocations(self):
        if self._fetchLocations and self.server_status:
            self.queue.put(["registered-chars"])

    def requestWormholes(self):
        self.queue.put(["thera_wormholes"])

    def fetchLocation(self, fetch=True):
        self._fetchLocations = fetch

    def run(self):
        while self.active:
            tsk = self.queue.get()
            logging.debug("MapStatisticsThread current task is : %s ", str(tsk))
            while tsk and len(tsk):
                if not self.active:
                    return
                statistics_data = dict({"result": "pending"})
                try:
                    if "server-status" in tsk:
                        self.server_status = True
                        statistics_data["server-status"] = evegate.esiStatus()
                        logging.info("EVE-Online Server status report : %s %s",
                                     statistics_data["server-status"], str(tsk))
                        self.queue.put(["statistics", "incursions", "campaigns", "sovereignty", "structures"])
                        tsk.remove("server-status")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "sovereignty" in tsk:
                        statistics_data["sovereignty"] = evegate.getPlayerSovereignty(fore_refresh=False, show_npc=True)
                        tsk.remove("sovereignty")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "structures" in tsk:
                        statistics_data["structures"] = evegate.esiSovereigntyStructures()
                        tsk.remove("structures")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "statistics" in tsk:
                        statistics_data["statistics"] = evegate.esiUniverseSystem_jumps()
                        tsk.remove("statistics")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "incursions" in tsk:
                        statistics_data["incursions"] = evegate.esiIncursions(False)
                        tsk.remove("incursions")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "campaigns" in tsk:
                        statistics_data["campaigns"] = evegate.getCampaignsSystemsIds(False)
                        tsk.remove("campaigns")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "registered-chars" in tsk:
                        statistics_data["registered-chars"] = evegate.esiGetCharsOnlineStatus()
                        tsk.remove("registered-chars")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "thera_wormholes" in tsk:
                        statistics_data["thera_wormhole"] = evegate.ESAPIListPublicSignatures()
                        tsk.remove("thera_wormholes")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if "thera_wormholes_version" in tsk:
                        res = evegate.ESAPIHealth()
                        if res:
                            statistics_data["thera_wormholes_version"] = res
                            self.queue.put(["thera_wormholes"])
                        else:
                            self.queue.put(["thera_wormholes_version"])
                        tsk.remove("thera_wormholes_version")
                        statistics_data["result"] = "ok"
                        self.statistic_data_update.emit(statistics_data)
                        continue

                except Exception as e:
                    self.server_status = False;
                    logging.error("MapStatisticsThread Error: %s %s", e, str(tsk))
                    statistics_data["result"] = "error"
                    statistics_data["text"] = str(e)
                    self.queue.put(["server-status"])
                    tsk = None

            if tsk and len(tsk):
                logging.debug("MapStatisticsThread fetching data succeeded, no queries left.")
        logging.debug("MapStatisticsThread terminated by application.")

    def quit(self):
        self.active = False
        self.queue.put(None)
        QThread.quit(self)
