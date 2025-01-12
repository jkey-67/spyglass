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
from PySide6.QtCore import QThread, QObject, QTimer, Qt
from PySide6.QtCore import Signal, Slot
from vi import evegate
from .cache.cache import Cache
from .resources import resourcePath
import weakref


class AvatarFindThread(QThread):
    avatar_update = Signal(object, object)
    fetch_avatar = Signal(weakref.ref)

    def __init__(self):
        QThread.__init__(self)
        self.cache = Cache()
        self.active = True
        self.last_call = 0
        self.min_wait = 500  # time between 2 requests in ms
        self.fetch_avatar.connect(self.process_chat_entry, Qt.ConnectionType.QueuedConnection)
        self.moveToThread(self)

    def addChatEntry(self, chat_entry, clear_cache=False):
        if self.active:
            try:
                if clear_cache:
                    self.cache.removeAvatar(chat_entry.message.user)
                self.fetch_avatar.emit(weakref.ref(chat_entry))
            except (Exception,) as e:
                logging.error("Error in AvatarFindThread: %s", e)

    @Slot(weakref.ref)
    def process_chat_entry(self, chat_entry_weakref):
        if self.isMainThread():
            logging.error("AvatarFindThread runs from main GUI thread")

        chat_entry = chat_entry_weakref()
        if chat_entry:
            user = chat_entry.message.user
            logging.debug("AvatarFindThread getting avatar for %s" % user)
            if user == "SPYGLASS":
                with open(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")), "rb") as f:
                    avatar = f.read()
            else:
                avatar = None

            if avatar is None:
                diff_last_call = time.time() - self.last_call
                if diff_last_call < self.min_wait:
                    time.sleep((self.min_wait - diff_last_call) / 1000.0)
                self.last_call = time.time()
                avatar = evegate.esiCharactersPortrait(user)

            if avatar:
                logging.debug("AvatarFindThread emit avatar_update for %s" % user)
                self.avatar_update.emit(chat_entry, avatar)
            else:
                logging.warning("AvatarFindThread unable to find avatar for %s" % user)

    def quit(self):
        if self.active:
            self.active = False
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
    CHECK_FOR_UPDATE ="check-for-update"


class RESULT:
    OK = "ok"
    ERROR = "error"


class MapStatisticsThread(QThread):
    """
    Fetching statistic data and player locations
    """
    statistic_data_update = Signal(dict)
    stat_query = Signal(list)

    def __init__(self):
        QThread.__init__(self)
        self.server_status = False
        self.active = True
        self.thera_system_name = None
        self._fetchLocations = True
        self.stat_query.connect(self.process_stat, Qt.ConnectionType.QueuedConnection)
        self.stat_query.emit([STAT.THERA_WORMHOLES_VERSION, STAT.SERVER_STATUS, STAT.CHECK_FOR_UPDATE])
        self.moveToThread(self)

    @Slot(list)
    def process_stat(self,query):
        if self.isMainThread():
            logging.warning("MapStatisticsThread current task is : {} runs from main gui thread isCurr:{} isCurr:{}".format(str(query), self.isCurrentThread(),self.isMainThread()))
        else:
            logging.debug("MapStatisticsThread current task is : {} isCurr:{} isMain:{}".format(str(query), self.isCurrentThread(),self.isMainThread()))
        while self.active and query and len(query):
            statistics_data = dict({STAT.RESULT: "pending"})
            try:
                if STAT.SERVER_STATUS in query:
                    if evegate.esiPing():
                        self.server_status = True
                        statistics_data[STAT.SERVER_STATUS] = evegate.esiStatus()
                        logging.info("EVE-Online Server status report : %s %s",
                                     statistics_data[STAT.SERVER_STATUS], str(query))
                        self.stat_query.emit([STAT.STATISTICS, STAT.INCURSIONS, STAT.CAMPAIGNS,
                                              STAT.SOVEREIGNTY, STAT.STRUCTURES, STAT.REGISTERED_CHARS])
                        query.remove(STAT.SERVER_STATUS)
                        statistics_data[STAT.RESULT] = RESULT.OK
                        self.statistic_data_update.emit(statistics_data)
                    else:
                        logging.info("EVE-Online Server seams to be down, will to reconnect in 5 sec.")
                        self.server_status = False
                        QTimer(self).singleShot(5000, self, self.requestStatistics)
                        query.remove(STAT.SERVER_STATUS)
                    continue

                if STAT.SOVEREIGNTY in query:
                    statistics_data[STAT.SOVEREIGNTY] = (
                        evegate.getPlayerSovereignty(show_npc=True))
                    query.remove(STAT.SOVEREIGNTY)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.STRUCTURES in query:
                    statistics_data[STAT.STRUCTURES] = evegate.esiSovereigntyStructures()
                    query.remove(STAT.STRUCTURES)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.STATISTICS in query:
                    statistics_data[STAT.STATISTICS] = evegate.esiUniverseSystem_jumps()
                    query.remove(STAT.STATISTICS)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.INCURSIONS in query:
                    statistics_data[STAT.INCURSIONS] = evegate.esiIncursions()
                    query.remove(STAT.INCURSIONS)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.CAMPAIGNS in query:
                    statistics_data[STAT.CAMPAIGNS] = evegate.getCampaignsSystemsIds()
                    query.remove(STAT.CAMPAIGNS)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.REGISTERED_CHARS in query:
                    statistics_data[STAT.REGISTERED_CHARS] = evegate.esiGetCharsOnlineStatus()
                    query.remove(STAT.REGISTERED_CHARS)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.THERA_WORMHOLES in query:
                    statistics_data[STAT.THERA_WORMHOLES] = evegate.checkTheraConnections(
                        evegate.ESAPIListPublicSignatures(), self.thera_system_name)
                    query.remove(STAT.THERA_WORMHOLES)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.OBSERVATIONS_RECORDS in query:
                    statistics_data[STAT.OBSERVATIONS_RECORDS] = evegate.ESAPIListPublicObservationsRecords()
                    query.remove(STAT.OBSERVATIONS_RECORDS)
                    statistics_data[STAT.RESULT] = RESULT.OK
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.THERA_WORMHOLES_VERSION in query:
                    res = evegate.ESAPIHealth()
                    if res:
                        logging.info("EVE-Scout Server status report : %s", res)
                        statistics_data[STAT.THERA_WORMHOLES_VERSION] = res
                        self.stat_query.emit([STAT.THERA_WORMHOLES, STAT.OBSERVATIONS_RECORDS])
                        statistics_data[STAT.RESULT] = RESULT.OK
                    else:
                        logging.info("EVE-Scout Server seams to be down, will to reconnect in 5 sec.")
                        QTimer(self).singleShot(5000, self, self.requestEVEScout)
                        statistics_data[STAT.RESULT] = RESULT.ERROR
                    query.remove(STAT.THERA_WORMHOLES_VERSION)
                    self.statistic_data_update.emit(statistics_data)
                    continue

                if STAT.CHECK_FOR_UPDATE in query:
                    res = evegate.checkSpyglassVersionUpdate()
                    if res:
                        statistics_data[STAT.CHECK_FOR_UPDATE] = res
                        statistics_data[STAT.RESULT] = RESULT.OK
                    else:
                        statistics_data[STAT.RESULT] = RESULT.ERROR
                    query.remove(STAT.CHECK_FOR_UPDATE)
                    self.statistic_data_update.emit(statistics_data)
                    continue

            except (Exception,) as e:
                self.server_status = False
                logging.error("MapStatisticsThread caught an exception: %s %s", e, str(query))
                statistics_data[STAT.RESULT] = RESULT.ERROR
                statistics_data[STAT.INFORMATION] = str(e)
                self.statistic_data_update.emit(statistics_data)
                self.stat_query.emit([STAT.THERA_WORMHOLES_VERSION, STAT.SERVER_STATUS])
                query = None


    @Slot()
    def requestEVEScout(self):
        if self.active:
            self.stat_query.emit([STAT.THERA_WORMHOLES_VERSION])

    @Slot()
    def requestSovereignty(self):
        if self.active:
            self.stat_query.emit([STAT.SOVEREIGNTY])

    @Slot()
    def requestStatistics(self):
        if self.active:
            if self.server_status:
                self.stat_query.emit([STAT.STATISTICS, STAT.INCURSIONS, STAT.CAMPAIGNS, STAT.STATISTICS, STAT.STRUCTURES])
            else:
                self.stat_query.emit([STAT.SERVER_STATUS])

    @Slot()
    def requestLocations(self):
        if self.active and self._fetchLocations and self.server_status:
            self.stat_query.emit([STAT.REGISTERED_CHARS])

    def setCurrentTheraSystem(self, system_name=None):
        if self.active:
            self.thera_system_name = system_name

    def requestWormholes(self):
        if self.active:
            self.stat_query.emit([STAT.THERA_WORMHOLES])

    def requestObservationsRecords(self):
        if self.active:
            self.stat_query.emit([STAT.OBSERVATIONS_RECORDS])

    def fetchLocation(self, fetch=True):
        if self.active:
            self._fetchLocations = fetch

    def quit(self):
        if self.active:
            self.active = False
            QThread.quit(self)
