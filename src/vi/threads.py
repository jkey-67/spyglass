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
import os
from dataclasses import dataclass
from functools import partial
from PySide6.QtCore import QThread, QObject, QTimer, Qt
from PySide6.QtCore import Signal, Slot
from vi import evegate
from .cache.cache import Cache
from .resources import resourcePath
import weakref


def queued_emit(signal, *args, **kwargs):
    """Emit a Qt signal via the event loop to enforce queued delivery."""
    QTimer.singleShot(0, partial(signal.emit, *args, **kwargs))


class AvatarFindThread(QThread):
    avatar_update = Signal(weakref.ref, object)
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
                queued_emit(self.fetch_avatar, weakref.ref(chat_entry))
            except (Exception,) as e:
                logging.error("Error in AvatarFindThread: %s", e)

    @Slot(weakref.ref)
    def process_chat_entry(self, chat_entry_weak_ref:weakref.ref):
        if self.isMainThread():
            logging.error("AvatarFindThread runs from main GUI thread")

        chat_entry = chat_entry_weak_ref()
        if chat_entry:
            user = chat_entry.message.user
            logging.debug("AvatarFindThread getting avatar for %s" % user)
            if user == "SPYGLASS":
                with open(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")), "rb") as f:
                    avatar = f.read()
            else:
                avatar = None

            if avatar is None:
                diff_last_call_ms = (time.time() - self.last_call) * 1000.0
                if diff_last_call_ms < self.min_wait:
                    time.sleep((self.min_wait - diff_last_call_ms) / 1000.0)
                self.last_call = time.time()
                avatar = evegate.esiCharactersPortrait(user)

            if avatar:
                logging.debug("AvatarFindThread emit avatar_update for %s" % user)
                queued_emit(self.avatar_update, chat_entry_weak_ref, avatar)
            else:
                logging.warning("AvatarFindThread unable to find avatar for %s" % user)

    def quit(self):
        if self.active:
            self.active = False
            QThread.quit(self)

@dataclass(frozen=True)
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
    CHECK_SDE_VERSION="sde_version-check"

class StatusDict(dict):
    def __init__(self):
        dict.__init__(self)
        self[STAT.RESULT] = "pending"
        self[STAT.RESULT] = RESULT.ERROR


@dataclass(frozen=True)
class RESULT:
    OK = "ok"
    ERROR = "error"


class MapStatisticsThread(QThread):
    """
    Fetching statistic data and player locations
    """
    statistic_data_update = Signal(object)
    stat_query = Signal(list)

    def __init__(self):
        QThread.__init__(self)
        self.server_status = False
        self.active = True
        self.thera_system_name = None
        self._fetchLocations = True
        self.stat_query.connect(self.process_stat, Qt.ConnectionType.QueuedConnection)
        self.moveToThread(self)

    def _fill_Query(self):
        queued_emit(self.stat_query, [STAT.THERA_WORMHOLES_VERSION, STAT.SERVER_STATUS,
                                      STAT.CHECK_FOR_UPDATE, STAT.CHECK_SDE_VERSION])
    def run(self):
        """Run the worker event loop and queue the initial statistics fetch inside the thread context."""
        try:
            logging.debug("MapStatisticsThread.run")
            QTimer.singleShot(
                0,
                self._fill_Query
            )
            QThread.run(self)
            logging.debug("MapStatisticsThread.run done.")
        except (Exception,) as ex:
            logging.error(f"MapStatisticsThread.run error : {ex}")

    @Slot(list)
    def process_stat(self,query):
        if not isinstance(query, (list, tuple)):
            logging.error("MapStatisticsThread received unexpected query type: %s", type(query))
            try:
                query = list(query) if query is not None else []
            except Exception:
                query = []
        else:
            query = list(query)
        if self.isMainThread():
            logging.warning("MapStatisticsThread current task is : {} runs from main gui thread isCurr:{} isCurr:{}".format(str(query), self.isCurrentThread(),self.isMainThread()))
        else:
            logging.debug("MapStatisticsThread current task is : {} isCurr:{} isMain:{}".format(str(query), self.isCurrentThread(),self.isMainThread()))
        while self.active and query and len(query):
            try:
                if STAT.SERVER_STATUS in query:
                    _data_SERVER_STATUS = StatusDict()
                    if evegate.esiPing():
                        self.server_status = True
                        _data_SERVER_STATUS[STAT.SERVER_STATUS] = evegate.esiStatus()
                        logging.info("EVE-Online Server status report : %s %s",
                                     _data_SERVER_STATUS[STAT.SERVER_STATUS], str(query))
                        queued_emit(self.stat_query, [STAT.STATISTICS, STAT.INCURSIONS, STAT.CAMPAIGNS,
                                                      STAT.SOVEREIGNTY, STAT.STRUCTURES, STAT.REGISTERED_CHARS])
                        query.remove(STAT.SERVER_STATUS)
                        _data_SERVER_STATUS[STAT.RESULT] = RESULT.OK
                        queued_emit(self.statistic_data_update, _data_SERVER_STATUS)
                        del _data_SERVER_STATUS
                    else:
                        logging.info("EVE-Online Server seams to be down, will to reconnect in 5 sec.")
                        self.server_status = False
                        QTimer.singleShot(5000, self.requestStatistics)
                        query.remove(STAT.SERVER_STATUS)
                    continue

                if STAT.CHECK_SDE_VERSION in query:
                    _data_CHECK_SDE_VERSION = StatusDict()
                    sde_version = evegate.getStaticDataVersion()
                    if sde_version:
                        _data_CHECK_SDE_VERSION[STAT.CHECK_SDE_VERSION] = sde_version
                        _data_CHECK_SDE_VERSION[STAT.RESULT] = RESULT.OK
                        query.remove(STAT.CHECK_SDE_VERSION)
                        queued_emit(self.statistic_data_update, _data_CHECK_SDE_VERSION)
                        del _data_CHECK_SDE_VERSION
                    else:
                        query.remove(STAT.CHECK_SDE_VERSION)
                        QTimer.singleShot(5000, self.requestSDEStatus)
                    continue

                if STAT.SOVEREIGNTY in query:
                    _data_SOVEREIGNTY = StatusDict()
                    _data_SOVEREIGNTY[STAT.SOVEREIGNTY] = (
                        evegate.getPlayerSovereignty(show_npc=True))
                    query.remove(STAT.SOVEREIGNTY)
                    _data_SOVEREIGNTY[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_SOVEREIGNTY)
                    del _data_SOVEREIGNTY
                    continue

                if STAT.STRUCTURES in query:
                    query.remove(STAT.STRUCTURES)
                    _data_STRUCTURES = StatusDict()
                    _data_STRUCTURES[STAT.STRUCTURES] = evegate.esiSovereigntyStructures()
                    _data_STRUCTURES[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_STRUCTURES)
                    continue

                if STAT.STATISTICS in query:
                    query.remove(STAT.STATISTICS)
                    _data_STATISTICS = StatusDict()
                    _data_STATISTICS[STAT.STATISTICS] = evegate.esiUniverseSystem_jumps()
                    _data_STATISTICS[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_STATISTICS)
                    del _data_STATISTICS
                    continue

                if STAT.INCURSIONS in query:
                    query.remove(STAT.INCURSIONS)
                    _data_INCURSIONS = StatusDict()
                    _data_INCURSIONS[STAT.INCURSIONS] = evegate.esiIncursions()
                    _data_INCURSIONS[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_INCURSIONS)
                    del _data_INCURSIONS
                    continue

                if STAT.CAMPAIGNS in query:
                    query.remove(STAT.CAMPAIGNS)
                    _data_CAMPAIGNS = StatusDict()
                    _data_CAMPAIGNS[STAT.CAMPAIGNS] = evegate.getCampaignsSystemsIds()
                    _data_CAMPAIGNS[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_CAMPAIGNS)
                    del _data_CAMPAIGNS
                    continue

                if STAT.REGISTERED_CHARS in query:
                    query.remove(STAT.REGISTERED_CHARS)
                    _data_REGISTERED_CHARS = StatusDict()
                    _data_REGISTERED_CHARS[STAT.REGISTERED_CHARS] = evegate.esiGetCharsOnlineStatus()
                    _data_REGISTERED_CHARS[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_REGISTERED_CHARS)
                    del _data_REGISTERED_CHARS
                    continue

                if STAT.THERA_WORMHOLES in query:
                    query.remove(STAT.THERA_WORMHOLES)
                    public_signatures = evegate.ESAPIListPublicSignatures(use_cache=False)
                    _data_THERA_WORMHOLES = StatusDict()
                    _data_THERA_WORMHOLES[STAT.THERA_WORMHOLES] = evegate.checkTheraConnections(
                        public_signatures, self.thera_system_name)
                    _data_THERA_WORMHOLES[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_THERA_WORMHOLES)
                    del _data_THERA_WORMHOLES
                    continue

                if STAT.OBSERVATIONS_RECORDS in query:
                    query.remove(STAT.OBSERVATIONS_RECORDS)
                    _data_OBSERVATIONS_RECORDS = StatusDict()
                    _data_OBSERVATIONS_RECORDS[STAT.OBSERVATIONS_RECORDS] = evegate.ESAPIListPublicObservationsRecords()
                    _data_OBSERVATIONS_RECORDS[STAT.RESULT] = RESULT.OK
                    queued_emit(self.statistic_data_update, _data_OBSERVATIONS_RECORDS)
                    del _data_OBSERVATIONS_RECORDS
                    continue

                if STAT.THERA_WORMHOLES_VERSION in query:
                    query.remove(STAT.THERA_WORMHOLES_VERSION)
                    _data_THERA_WORMHOLES_VERSION = StatusDict()
                    res = evegate.ESAPIHealth()
                    if res:
                        logging.info("EVE-Scout Server status report : %s", res)
                        _data_THERA_WORMHOLES_VERSION[STAT.THERA_WORMHOLES_VERSION] = res
                        queued_emit(self.stat_query, [STAT.THERA_WORMHOLES, STAT.OBSERVATIONS_RECORDS])
                        _data_THERA_WORMHOLES_VERSION[STAT.RESULT] = RESULT.OK
                    else:
                        logging.info("EVE-Scout Server seams to be down, will to reconnect in 5 sec.")
                        QTimer.singleShot(5000, self.requestEVEScout)
                        _data_THERA_WORMHOLES_VERSION[STAT.RESULT] = RESULT.ERROR
                    queued_emit(self.statistic_data_update, _data_THERA_WORMHOLES_VERSION)
                    del _data_THERA_WORMHOLES_VERSION
                    continue

                if STAT.CHECK_FOR_UPDATE in query:
                    query.remove(STAT.CHECK_FOR_UPDATE)
                    _data_CHECK_FOR_UPDATE = StatusDict()
                    res = evegate.checkSpyglassVersionUpdate()
                    if res:
                        _data_CHECK_FOR_UPDATE[STAT.CHECK_FOR_UPDATE] = res
                        _data_CHECK_FOR_UPDATE[STAT.RESULT] = RESULT.OK
                    else:
                        _data_CHECK_FOR_UPDATE[STAT.RESULT] = RESULT.ERROR
                    queued_emit(self.statistic_data_update, _data_CHECK_FOR_UPDATE)
                    del _data_CHECK_FOR_UPDATE
                    continue

            except (Exception,) as e:
                self.server_status = False
                logging.error("MapStatisticsThread caught an exception: %s %s", e, str(query))
                _data_ERROR = StatusDict()
                _data_ERROR[STAT.RESULT] = RESULT.ERROR
                _data_ERROR[STAT.INFORMATION] = str(e)
                queued_emit(self.statistic_data_update, _data_ERROR)
                del _data_ERROR
                QTimer.singleShot(5000, self.requestServerStatus)
                query = None
        logging.debug(
            "MapStatisticsThread current task is : {} isCurr:{} isMain:{} done.".format(str(query), self.isCurrentThread(),
                                                                                  self.isMainThread()))
    @Slot()
    def requestServerStatus(self):
        logging.debug("MapStatisticsThread.requestServerStatus.")
        queued_emit(self.stat_query, [STAT.THERA_WORMHOLES_VERSION, STAT.SERVER_STATUS, STAT.CHECK_SDE_VERSION])
        logging.debug("MapStatisticsThread.requestServerStatus done.")


    @Slot()
    def requestEVEScout(self):
        logging.debug("MapStatisticsThread.requestEVEScout.")
        if self.active:
            queued_emit(self.stat_query, [STAT.THERA_WORMHOLES_VERSION])
        logging.debug("MapStatisticsThread.requestEVEScout done.")

    @Slot()
    def requestSovereignty(self):
        logging.debug("MapStatisticsThread.requestSovereignty")
        if self.active:
            queued_emit(self.stat_query, [STAT.SOVEREIGNTY])
        logging.debug("MapStatisticsThread.requestSovereignty done.")

    @Slot()
    def requestStatistics(self):
        logging.debug("MapStatisticsThread.requestStatistics")
        if self.active:
            if self.server_status:
                queued_emit(self.stat_query, [STAT.STATISTICS, STAT.INCURSIONS, STAT.CAMPAIGNS, STAT.STRUCTURES])
            else:
                queued_emit(self.stat_query, [STAT.SERVER_STATUS])
        logging.debug("MapStatisticsThread.requestStatistics done.")
    @Slot()
    def requestSDEStatus(self):
        logging.debug("MapStatisticsThread.requestSDEStatus")
        if self.active:
            queued_emit(self.stat_query, [STAT.CHECK_SDE_VERSION])
        logging.debug("MapStatisticsThread.requestSDEStatus done.")

    @Slot()
    def requestLocations(self):
        logging.debug("MapStatisticsThread.requestLocations")
        if self.active and self._fetchLocations and self.server_status:
            queued_emit(self.stat_query, [STAT.REGISTERED_CHARS])
        logging.debug("MapStatisticsThread.requestLocations done.")

    def setCurrentTheraSystem(self, system_name=None):
        logging.debug("MapStatisticsThread.setCurrentTheraSystem ")
        if self.active:
            self.thera_system_name = system_name
        logging.debug("MapStatisticsThread.setCurrentTheraSystem done.")

    def requestWormholes(self):
        logging.debug("MapStatisticsThread.requestWormholes ")
        if self.active:
            queued_emit(self.stat_query, [STAT.THERA_WORMHOLES])
        logging.debug("MapStatisticsThread.requestWormholes done")

    def requestObservationsRecords(self):
        logging.debug("MapStatisticsThread.requestObservationsRecords ")
        if self.active:
            queued_emit(self.stat_query, [STAT.OBSERVATIONS_RECORDS])
        logging.debug("MapStatisticsThread.requestObservationsRecords done.")

    def fetchLocation(self, fetch=True):
        logging.debug("MapStatisticsThread.fetchLocation")
        if self.active:
            self._fetchLocations = fetch
        logging.debug("MapStatisticsThread.fetchLocation done.")

    def quit(self):
        logging.debug("MapStatisticsThread.quit")
        if self.active:
            self.active = False
            QThread.quit(self)
