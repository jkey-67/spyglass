"""Integration helpers for consuming the zKillboard RedisQ feed.

This module polls RedisQ, converts kill mails into Spyglass' UTF-16 encoded
log format, caches the raw payloads for later lookup, and emits Qt signals so
the UI can react to kill events in real time.
"""

import json
import logging
import os.path
import datetime
import time

import PySide6.QtNetwork
from PySide6.QtCore import QUrl, QObject, QTimer
from PySide6.QtCore import Signal, Qt
from PySide6.QtNetwork import QNetworkRequest
from PySide6.QtNetwork import QNetworkReply
from PySide6.QtNetwork import QNetworkAccessManager
from .evegate import esiUniverseNames, esiAlliances
from .universe import Universe
from .cache import Cache
from .chatparser.ctx import CTX
import uuid

def getTickMs()->int:
     return int(time.time()*1000.0)

class ZKillMonitor(QObject):
    """Subscribe to the zKillboard RedisQ stream and surface kills to Spyglass.

    The monitor uses HTTP long-polling to receive messages, writes formatted
    kill intel to ``zkillMonitor.log`` in UTF-16 LE, and caches the raw
    killmail JSON for other components.

    If USE_R2Z2 is true
        https://github.com/zKillboard/zKillboard/wiki/API-(R2Z2)
    otherwise
        https://github.com/zKillboard/RedisQ

    Attributes:
        status_kill_mail: Emits True when a killmail is processed, False on
            failures.
        report_system_kill: Emits a solar system ID for every killmail.
    """
    status_kill_mail = Signal(bool)
    report_system_kill = Signal(int,float)
    MONITORING_PATH = "zkillMonitor.log"
    LOG_VICTIM = True               # logs if a blue alliance is in victims
    LOG_ATTACKERS = False           # logs if a blue alliance is in attackers
    LOG_ALL_KILL_MAILS = False      # log all messages, for debugging only
    USE_R2Z2 = True
    UTF16_BOM = u'\uFEFF\n'

    def __init__(self, parent=None):
        """Initialize the zKillboard monitor and networking state.

        Args:
            parent: Optional QObject parent.

        Returns:
            None.
        """
        QObject.__init__(self,parent=parent)
        self.writeHeader()
        self.zkillredisqStreamID = Cache().getFromCache("zkillredisq.stream.id")
        if self.zkillredisqStreamID is None:
            self.zkillredisqStreamID = "spyglass-{}".format(uuid.uuid4())
            Cache().putIntoCache("zkillredisq.stream.id", self.zkillredisqStreamID)
        # self.zkillredisqStreamID = "spyglass-{}".format(uuid.uuid4())
        self.netManager = QNetworkAccessManager()
        self.netSequenceReader = QNetworkAccessManager()
        if ZKillMonitor.USE_R2Z2:
            self.netManager.finished.connect(self._responseSequenceJsonReady, Qt.ConnectionType.QueuedConnection)
            self.netSequenceReader.finished.connect(self._responseSequenceReady, Qt.ConnectionType.QueuedConnection)
        else:
            self.netManager.finished.connect(self._responseReady, Qt.ConnectionType.QueuedConnection)
        self.killmailManager = QNetworkAccessManager()
        self.killmailManager.finished.connect(self.killmailResponseReady,Qt.ConnectionType.QueuedConnection)
        self.pendingKillmailReplies = dict()
        self.req = QNetworkRequest()
        self.reqSequence = QNetworkRequest()
        self.sequence = None
        self.reply = None
        self.reply_sequence = None

        if ZKillMonitor.USE_R2Z2:
            self.req.setUrl("https://r2z2.zkillboard.com/ephemeral/sequence.json")
        else:
            self.req.setUrl("https://zkillredisq.stream/listen.php?queueID={}".format(self.zkillredisqStreamID))
        self.last_query = getTickMs()

    def _waitTimeMS(self, delta:int)->int:
        return max(0,delta - (getTickMs() - self.last_query))

    def _getNextSequence(self):
        self.reqSequence.setUrl("https://r2z2.zkillboard.com/ephemeral/{}.json".format(self.sequence))
        if self.reply_sequence:
            self.reply_sequence.deleteLater()
        self.reply_sequence = self.netSequenceReader.get(self.reqSequence)
        self.last_query = getTickMs()
        logging.debug( "GET ({} ms) https://r2z2.zkillboard.com/ephemeral/{}.json".format(self.last_query,self.sequence))

    def _responseSequenceReady(self, reply:QNetworkReply):
        try:
            if reply.error() == PySide6.QtNetwork.QNetworkReply.NetworkError.NoError:
                sequence_data = json.loads(reply.readAll().data())
                if self.processKillPackage(sequence_data, reply.url().toString()):
                    self.status_kill_mail.emit(True)
                self.sequence = sequence_data.get("sequence_id")
                if self.sequence:
                    self.sequence += 1
                    QTimer.singleShot(self._waitTimeMS(100), self._getNextSequence)
                    return
            elif reply.error() == PySide6.QtNetwork.QNetworkReply.NetworkError.ContentNotFoundError:  # 404
                QTimer.singleShot(self._waitTimeMS(6000), self._getNextSequence)
                return
            else:
                logging.error(
                    "Error {} : {}".format(
                        reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute), reply.errorString()))

        except (Exception,) as ex:
            logging.error(
                "Error : {} during the handling of an zKillboard message {}".format(ex, reply.url().toString()))
        self.status_kill_mail.emit(False)
        QTimer.singleShot(6000, self.startConnect)

    def _responseSequenceJsonReady(self, reply:QNetworkReply):
        """Handle one RedisQ HTTP reply.

        Args:
            reply: Network reply returned by the long-poll request.

        Returns:
            None.

        Side Effects:
            Emits ``status_kill_mail`` when a killmail is parsed and schedules
            the next request.
        """
        try:
            if reply.error() == PySide6.QtNetwork.QNetworkReply.NetworkError.NoError:
                self.sequence = json.loads(reply.readAll().data()).get("sequence")
                if self.sequence:
                    self._getNextSequence()
                    return
            elif reply.error() == PySide6.QtNetwork.QNetworkReply.NetworkError.ContentNotFoundError:  # 404
                self.reply.deleteLater()
                QTimer.singleShot(self._waitTimeMS(6000), self._getNextSequence)
                return
            else:
                logging.error(
                    "Error {} : {}".format(
                        reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute), reply.errorString()))

        except (Exception,) as ex:
            logging.error(
                "Error : {} during the handling of an zKillboard message {}".format(ex, reply.url().toString()))
        if self.reply:
            self.reply.deleteLater()
            self.reply = None
        self.status_kill_mail.emit(False)
        QTimer.singleShot(6000, self.startConnect)

    def _responseReady(self, reply:QNetworkReply):
        """Handle one RedisQ HTTP reply.

        Args:
            reply: Network reply returned by the long-poll request.

        Returns:
            None.

        Side Effects:
            Emits ``status_kill_mail`` when a killmail is parsed and schedules
            the next request.
        """


        try:
            if reply.error() == PySide6.QtNetwork.QNetworkReply.NetworkError.NoError:
                processed = self.onNewTextMessage(json.loads(reply.readAll().data()), reply.url().toString())
                if processed:
                    self.status_kill_mail.emit(True)
            else:
                logging.error(
                    "Error {} : {}".format(
                        reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute), reply.errorString()))
                self.status_kill_mail.emit(False)
        except (Exception,)as ex:
            logging.error("Error : {} during the handling of an zKillboard message {}".format(ex, reply.url().toString()))
            self.status_kill_mail.emit(False)

        if self.reply:
            self.reply.deleteLater()
            self.reply = self.netManager.get(self.req)

    def _restartConnect(self):
        self.reply = self.netManager.get(self.req)

    def startConnect(self):
        """Start polling zKillboard via RedisQ.

        Returns:
            None.
        """
        logging.info("zKillboard message processing started.")
        self.status_kill_mail.emit(False)
        self.reply = self.netManager.get(self.req)

    def startDisconnect(self):
        """Stop polling zKillboard.

        Returns:
            None.
        """
        logging.info("zKillboard message processing terminated.")
        self.reply = None

    @staticmethod
    def writeUTF16BOM(fp, txt):
        """Write text prefixed with the UTF-16 BOM expected by the log file.

        Args:
            fp: Opened file pointer with UTF-16 encoding.
            txt: Text to write.

        Returns:
            None.
        """
        fp.write(ZKillMonitor.UTF16_BOM + txt)

    @staticmethod
    def writeHeader():
        """Create the zKillboard log with the expected header if it is missing.

        Returns:
            None.
        """
        if not os.path.exists(ZKillMonitor.MONITORING_PATH):
            with open(ZKillMonitor.MONITORING_PATH, "wt", encoding="utf-16-le") as fp:
                ZKillMonitor.writeUTF16BOM(fp, u'\n')
                ZKillMonitor.writeUTF16BOM(fp, u'\n')
                ZKillMonitor.writeUTF16BOM(fp, u'\n')
                ZKillMonitor.writeUTF16BOM(fp, u"---------------------------------------------------------------\n")
                ZKillMonitor.writeUTF16BOM(fp, u"Channel ID: zKillboard\n")
                ZKillMonitor.writeUTF16BOM(fp, u"Channel Name: zKillboard\n")
                ZKillMonitor.writeUTF16BOM(fp, u"---------------------------------------------------------------\n")
                ZKillMonitor.writeUTF16BOM(fp, u"Websocket listen to url wss://zkillboard.com/websocket/\n")
                ZKillMonitor.writeUTF16BOM(fp, u"---------------------------------------------------------------\n")
                ZKillMonitor.writeUTF16BOM(fp, u"\n")
                ZKillMonitor.writeUTF16BOM(fp, u"\n")
                ZKillMonitor.writeUTF16BOM(fp, u"\n")

    def processKillPackage(self, package_data: dict, source_url: str = None) -> bool:
        """Process a killmail package that already contains the killmail.

        Args:
            package_data: Package dict that must include ``killmail`` once populated.
            source_url: URL the package came from, used only for logging.

        Returns:
            bool: True when the package was handled (even if not logged).
        """
        killmail = package_data.get("killmail")
        if not killmail:
            killmail = package_data.get("esi")

        if not killmail:
            return False

        solar_system_id = killmail.get("solar_system_id")
        killmail_time = killmail.get("killmail_time")

        if solar_system_id is not None:
            kill_time = datetime.datetime.strptime(killmail_time, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc).timestamp()
            self.report_system_kill.emit(solar_system_id, kill_time)

        self.logKillMail(killmail)
        if self.logKillAsIntel(killmail):
            kill_string = self.getIntelString(package_data)
            self.writeHeader()
            with open(ZKillMonitor.MONITORING_PATH, "at", encoding='utf-16-le') as fp:
                ZKillMonitor.writeUTF16BOM(fp, kill_string)
            if source_url:
                logging.debug("new zKillboard message {}".format(source_url))
        return True

    def fetchKillmail(self, href: str, package_data: dict):
        """Fetch the killmail JSON via Qt networking instead of requests.

        Args:
            href: Absolute URL to fetch the killmail from.
            package_data: Package dict to augment with the fetched killmail.

        Returns:
            None.
        """
        request = QNetworkRequest(QUrl(href))
        reply = self.killmailManager.get(request)
        self.pendingKillmailReplies[reply] = package_data

    def killmailResponseReady(self, reply: QNetworkReply):
        """Handle killmail fetch replies.

        Args:
            reply: Network reply returned by the killmail fetch.

        Returns:
            None.
        """
        package_data = self.pendingKillmailReplies.pop(reply, None)
        if package_data is None:
            reply.deleteLater()
            return
        else:
            try:
                if reply.error() == PySide6.QtNetwork.QNetworkReply.NetworkError.NoError:
                    package_data["killmail"] = json.loads(reply.readAll().data())
                    processed = self.processKillPackage(package_data, reply.url().toString())
                    if processed:
                        self.status_kill_mail.emit(True)
                else:
                    logging.error(
                        "Error {} : {}".format(
                            reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute), reply.errorString()))
                    self.status_kill_mail.emit(False)
            except (Exception,) as ex:
                logging.error("Error : {} during the handling of an zKillboard message {}".format(ex, reply.url().toString()))
                self.status_kill_mail.emit(False)
            finally:
                reply.deleteLater()

    def onNewTextMessage(self,data:dict, source_url: str = None)->bool:
        """Process one RedisQ message payload.

        Args:
            data: JSON-decoded dictionary returned by RedisQ.
            source_url: The URL associated with the incoming reply, used for logging.

        Returns:
            bool: True if a killmail was parsed and written; False when the
            payload was empty, discarded, or waiting for a follow-up fetch.
        """
        if data:
            package  = data["package"] if "package" in data.keys() else None
            killmail = package["killmail"] if  package and "killmail" in  package.keys() else None
            zkb = package["zkb"] if package and "zkb" in package.keys() else None
            if zkb and not killmail and "href" in zkb.keys():
                self.fetchKillmail(zkb["href"], package)
            elif killmail:
                return self.processKillPackage(package, source_url)
        return False

    @staticmethod
    def logKillMail(kill_data:dict):
        """Persist raw killmail JSON and metadata to the cache.

        Args:
            kill_data: Killmail dictionary from the RedisQ package.

        Returns:
            None.
        """
        kill_time = datetime.datetime.strptime(kill_data["killmail_time"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc)
        Cache().putKillmailtoCache(
            killmail_id=kill_data["killmail_id"],
            region_id=Universe.regionIDFromSystemID(kill_data["solar_system_id"]),
            system_id=kill_data["solar_system_id"],
            modified=kill_time.timestamp(),
            json_txt=json.dumps(kill_data)
        )

    @staticmethod
    def getIntelString(package_data:dict) -> str:
        """Format a killmail package into the UTF-16 log string.

        Args:
            package_data: Full RedisQ package including ``killmail`` and
                ``killID`` fields.

        Returns:
            str: Intel line ready to be written to the zKillboard log.
        """
        if ZKillMonitor.USE_R2Z2:
            kill_data = package_data["esi"] if "esi" in package_data.keys() else dict()
            kill_url = "https://zkillboard.com/kill/{}/".format(package_data["killmail_id"] if "killmail_id" in package_data.keys() else "")
        else:
            kill_data = package_data["killmail"] if "killmail" in package_data.keys() else dict()
            kill_url = "https://zkillboard.com/kill/{}/".format(package_data["killID"] if "killID" in package_data.keys() else "")

        victim = kill_data["victim"] if "victim" in kill_data.keys() else dict()
        zk_time = kill_data["killmail_time"] if "killmail_time" in kill_data.keys() else ""
        system_id = kill_data["solar_system_id"] if "solar_system_id" in kill_data.keys() else dict()
        zkb_data = package_data["zkb"] if "zkb" in package_data.keys() else dict()


        """
          Date encoding like
          0---------1--------"
          0123456789012345678"
          2023.05.26 19:08:11"
          2023-10-22T07:53:16Z"
        """
        kill_time = "{}.{}.{} {}".format(zk_time[0:4], zk_time[5:7], zk_time[8:10], zk_time[11:19])

        character_id = victim["character_id"] if "character_id" in victim.keys() else 0
        ship_type_id = victim["ship_type_id"] if "ship_type_id" in victim.keys() else 0
        alliance_id = victim["alliance_id"] if "alliance_id" in victim.keys() else 0
        total_value = "<br/>Total Value : {:,} ISK".format( zkb_data["totalValue"]) if "totalValue" in zkb_data.keys() else ""

        if alliance_id:
            user_data = esiUniverseNames({character_id, system_id, ship_type_id, alliance_id})
        else:
            user_data = esiUniverseNames({character_id, system_id, ship_type_id})

        kill_victim_character = user_data[character_id] if character_id and character_id in user_data.keys() else "-"
        kill_victim_ship_type = user_data[ship_type_id] if ship_type_id and ship_type_id in user_data.keys() else "-"
        kill_victim_alliance = user_data[alliance_id] if alliance_id and alliance_id in user_data.keys() else "-"
        kill_system_name = Universe.systemNameById(system_id)
        alliance_ticker = ""
        if alliance_id:
            message_msk = \
                "[ {date} ] zKillboard.com >{link}<br/>{player} &lt;{ticker}&gt;({alliance}) lost their {ship}"\
                " in {system}.{value}\n"
            alliance_ticker = esiAlliances(alliance_id)["ticker"]
        else:
            message_msk = "[ {date} ] zKillboard.com >{link}<br/>{player} lost their {ship} in {system}.{value}\n"

        return message_msk.format(
            date=kill_time,
            system=" {} ".format(kill_system_name),
            ticker=alliance_ticker,
            player=CTX.FORMAT_PLAYER_NAME.format(kill_victim_character, character_id),
            alliance=CTX.FORMAT_ALLIANCE_NAME.format(kill_victim_alliance, alliance_id),
            ship=CTX.FORMAT_SHIP.format(kill_victim_ship_type,kill_victim_ship_type),
            link=CTX.FORMAT_URL.format(kill_url),
            value=CTX.FORMAT_VALUE.format(total_value)
        )

    @staticmethod
    def updateKillDatabase(kill_data:dict):
        """Check if the victim belongs to a blue alliance.

        Args:
            kill_data: Killmail dictionary to evaluate.

        Returns:
            bool: True when the victim alliance is blue.
        """
        victim = kill_data["victim"] if "victim" in kill_data.keys() else None
        alliance_id = victim["alliance_id"] if victim and "alliance_id" in victim.keys() else 0
        return alliance_id in Cache().getAllianceBlue()

    @staticmethod
    def logKillAsIntel(kill_data:dict) -> bool:
        """Decide whether the kill should be recorded as intel.

        Args:
            kill_data: Killmail dictionary to evaluate.

        Returns:
            bool: True when the kill should be logged as intel.

        Notes:
            The decision is controlled by the ``LOG_VICTIM`` and
            ``LOG_ATTACKERS`` flags and checks alliance IDs against the cached
            blue list.
        """

        if ZKillMonitor.LOG_ALL_KILL_MAILS:
            return True

        blue_alliances = Cache().getAllianceBlue()

        if ZKillMonitor.LOG_VICTIM:
            victim = kill_data["victim"] if "victim" in kill_data.keys() else None
            if "character_id" in victim.keys():
                if "alliance_id" in victim.keys():
                    alliance_id = victim["alliance_id"]
                    if alliance_id in blue_alliances:
                        return True

        if ZKillMonitor.LOG_ATTACKERS:
            for attacker in kill_data["attackers"]:
                if "alliance_id" in attacker.keys():
                    alliance_id = attacker["alliance_id"]
                    if alliance_id in blue_alliances:
                        return True

        return False
