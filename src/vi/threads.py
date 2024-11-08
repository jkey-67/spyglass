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
from PySide6.QtCore import QThread, QObject
from PySide6.QtCore import Signal, Slot
from vi import evegate
from .cache.cache import Cache
from .resources import resourcePath
import weakref


class AvatarFindThread(QThread):
    avatar_update = Signal(object, object)

    def __init__(self):
        QThread.__init__(self)
        self.cache = Cache()
        self.queue = queue.Queue()
        self.active = True

    def addChatEntry(self, chat_entry, clear_cache=False):
        try:
            if clear_cache:
                self.cache.removeAvatar(chat_entry.message.user)
            chat_entry.destroyed.connect(self.entryDestroyed)
            self.queue.put(weakref.ref(chat_entry))
        except (Exception,) as e:
            logging.error("Error in AvatarFindThread: %s", e)

    @Slot(QObject)
    def entryDestroyed(self, elem):
        logging.debug("Error in AvatarFindThread element destroyed.")

    def run(self):
        last_call = 0
        wait = 500  # time between 2 requests in ms
        while self.active:
            try:
                # Block waiting for addChatEntry() to enqueue something
                weak_chat_entry = self.queue.get()
                if weak_chat_entry is None:
                    logging.debug("AvatarFindThread termination started")
                    continue
                chat_entry = weak_chat_entry()
                if chat_entry is None:
                    logging.debug("AvatarFindThread chat entry expired.")
                    continue
                user = chat_entry.message.user
                logging.debug("AvatarFindThread getting avatar for %s" % user)

                if user == "SPYGLASS":
                    with open(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")), "rb") as f:
                        avatar = f.read()
                else:
                    avatar = None

                if avatar is None:
                    diff_last_call = time.time() - last_call
                    if diff_last_call < wait:
                        time.sleep((wait - diff_last_call) / 1000.0)
                    last_call = time.time()
                    # fetch data to
                    avatar = evegate.esiCharactersPortrait(user)
                if avatar:
                    logging.debug("AvatarFindThread emit avatar_update for %s" % user)
                    chat_entry.destroyed.disconnect(self.entryDestroyed)
                    self.avatar_update.emit(chat_entry, avatar)
                else:
                    logging.warning("AvatarFindThread unable to find avatar for %s" % user)
            except (Exception,) as e:
                logging.error("AvatarFindThread cough exception: %s", e)

    def quit(self):
        self.active = False
        self.queue.put(None)
        QThread.quit(self)


class STAT:
    SOVEREIGNTY = "sovereignty"
    THERA_WORMHOLES_VERSION = "thera_wormholes_version"
    SERVER_STATUS = "server-status"
    STATISTICS = "statistics"
    INCURSIONS = "incursions"
    CAMPAIGNS = "campaigns"
    STRUCTURES = "structures"
    REGISTERED_CHARS = "registered-chars"
    THERA_WORMHOLES = "thera_wormholes"
    OBSERVATIONS_RECORDS = "observations_records"
    RESULT = "result"
    INFORMATION = "information"


class RESULT:
    OK = "ok"
    ERROR = "error"


class MapStatisticsThread(QThread):
    """
    Fetching statistic data and player locations
    """
    statistic_data_update = Signal(dict)

    def __init__(self):
        QThread.__init__(self)
        self.queue = queue.Queue(maxsize=10)
        self.server_status = False
        self.active = True
        self.thera_system_name = None
        self._fetchLocations = True
        self.queue.put([STAT.THERA_WORMHOLES_VERSION, STAT.SERVER_STATUS])

    def requestSovereignty(self):
        self.queue.put([STAT.SOVEREIGNTY])

    def requestStatistics(self):
        if self.server_status:
            self.queue.put([STAT.STATISTICS, STAT.INCURSIONS, STAT.CAMPAIGNS, STAT.STATISTICS, STAT.STRUCTURES])
        else:
            self.queue.put([STAT.SERVER_STATUS])

    def requestLocations(self):
        if self._fetchLocations and self.server_status:
            self.queue.put([STAT.REGISTERED_CHARS])

    def setCurrentTheraSystem(self, system_name=None):
        self.thera_system_name = system_name

    def requestWormholes(self):
        self.queue.put([STAT.THERA_WORMHOLES])

    def requestObservationsRecords(self):
        self.queue.put([STAT.OBSERVATIONS_RECORDS])

    def fetchLocation(self, fetch=True):
        self._fetchLocations = fetch

    def run(self):
        while self.active:
            tsk = self.queue.get()
            logging.debug("MapStatisticsThread current task is : %s ", str(tsk))
            while tsk and len(tsk):
                if not self.active:
                    return
                statistics_data = dict({STAT.RESULT: "pending"})
                try:
                    if STAT.SERVER_STATUS in tsk:
                        self.server_status = True
                        if evegate.esiPing():
                            statistics_data[STAT.SERVER_STATUS] = evegate.esiStatus()
                            logging.info("EVE-Online Server status report : %s %s",
                                         statistics_data[STAT.SERVER_STATUS], str(tsk))
                            self.queue.put([STAT.STATISTICS, STAT.INCURSIONS, STAT.CAMPAIGNS,
                                            STAT.SOVEREIGNTY, STAT.STRUCTURES, STAT.REGISTERED_CHARS])
                            tsk.remove(STAT.SERVER_STATUS)
                            statistics_data[STAT.RESULT] = RESULT.OK
                            self.statistic_data_update.emit(statistics_data)
                        else:
                            tsk = None
                            self.queue.put([STAT.SERVER_STATUS])
                            self.sleep(2)
                        continue

                    if STAT.SOVEREIGNTY in tsk:
                        statistics_data[STAT.SOVEREIGNTY] = (
                            evegate.getPlayerSovereignty(fore_refresh=False, show_npc=True))
                        tsk.remove(STAT.SOVEREIGNTY)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.STRUCTURES in tsk:
                        statistics_data[STAT.STRUCTURES] = evegate.esiSovereigntyStructures()
                        tsk.remove(STAT.STRUCTURES)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.STATISTICS in tsk:
                        statistics_data[STAT.STATISTICS] = evegate.esiUniverseSystem_jumps()
                        tsk.remove(STAT.STATISTICS)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.INCURSIONS in tsk:
                        statistics_data[STAT.INCURSIONS] = evegate.esiIncursions(False)
                        tsk.remove(STAT.INCURSIONS)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.CAMPAIGNS in tsk:
                        statistics_data[STAT.CAMPAIGNS] = evegate.getCampaignsSystemsIds(False)
                        tsk.remove(STAT.CAMPAIGNS)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.REGISTERED_CHARS in tsk:
                        statistics_data[STAT.REGISTERED_CHARS] = evegate.esiGetCharsOnlineStatus()
                        tsk.remove(STAT.REGISTERED_CHARS)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.THERA_WORMHOLES in tsk:
                        statistics_data[STAT.THERA_WORMHOLES] = evegate.checkTheraConnections(
                            evegate.ESAPIListPublicSignatures(), self.thera_system_name)
                        tsk.remove(STAT.THERA_WORMHOLES)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.OBSERVATIONS_RECORDS in tsk:
                        statistics_data[STAT.OBSERVATIONS_RECORDS] = evegate.ESAPIListPublicObservationsRecords()
                        tsk.remove(STAT.OBSERVATIONS_RECORDS)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                    if STAT.THERA_WORMHOLES_VERSION in tsk:
                        res = evegate.ESAPIHealth()
                        if res:
                            statistics_data[STAT.THERA_WORMHOLES_VERSION] = res
                            self.queue.put([STAT.THERA_WORMHOLES, STAT.OBSERVATIONS_RECORDS])
                        else:
                            self.queue.put([STAT.THERA_WORMHOLES_VERSION])
                        tsk.remove(STAT.THERA_WORMHOLES_VERSION)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                        continue

                except (Exception,) as e:
                    self.server_status = False
                    logging.error("MapStatisticsThread caught an exception: %s %s", e, str(tsk))
                    statistics_data[STAT.RESULT] = RESULT.ERROR
                    statistics_data[STAT.INFORMATION] = str(e)
                    self.statistic_data_update.emit(statistics_data)
                    tsk = None

            if tsk and len(tsk):
                logging.debug("MapStatisticsThread fetching data succeeded, no queries left.")
        logging.debug("MapStatisticsThread terminated by application.")

    def quit(self):
        self.active = False
        self.queue.put(None)
        QThread.quit(self)
