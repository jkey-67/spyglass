import json
import logging
import os.path
import datetime

from PySide6.QtCore import QUrl, QObject, QTimer
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtCore import Signal

from .evegate import esiUniverseNames, esiAlliances
from .universe import Universe
from .cache import Cache
from .chatparser.ctx import CTX

UTF16_BOM = u'\uFEFF\n'


class ZKillMonitor(QObject):
    """
        Converts the websocket stream to a compatible logfile, the file encoding is "utf-16-le"
        see: https://github.com/zKillboard/zKillboard/wiki
    """
    status_kill_mail = Signal(bool)
    report_system_kill = Signal(int)
    MONITORING_PATH = "zkillMonitor.log"
    LOG_VICTIM = True
    LOG_ATTACKERS = False

    def __init__(self, parent=None, address='wss://zkillboard.com/websocket/'):
        QObject.__init__(self)
        self._writeHeader()
        self.address = address
        self.webSocket = QWebSocket(parent=parent)
        self.webSocket.ignoreSslErrors()
        self.webSocket.error.connect(self.onError)
        self.webSocket.errorOccurred.connect(self.onError)
        self.webSocket.connected.connect(self.onConnected)
        self.webSocket.disconnected.connect(self.onClosed)
        self.webSocket.textMessageReceived.connect(self.onNewTextMessage)
        self.reconnectTimer = QTimer(parent=parent)
        self.reconnectTimer.setInterval(10000)
        self.reconnectTimer.setSingleShot(True)
        self.reconnectTimer.timeout.connect(self.startConnectFromTimer)
        self.reconnectTimer.start()

    def startConnectFromTimer(self):
        self.status_kill_mail.emit(False)
        logging.info("Websocket reconnecting to url {}".format(self.address))
        self.webSocket.open(QUrl(self.address))

    def startConnect(self):
        self.status_kill_mail.emit(False)
        return

    def startDisconnect(self):
        logging.info("Websocket disconnecting from url {}".format(self.address))
        if self.reconnectTimer.isActive():
            self.reconnectTimer.stop()
        self.webSocket.close()

    def onError(self):
        self.status_kill_mail.emit(False)
        logging.error("Websocket  error {} url: {}".format(self.webSocket.errorString(), self.address))

    def onConnected(self):
        self.status_kill_mail.emit(True)
        logging.info("Websocket connected to url {} {} {}".format(
            self.address, self.webSocket.version(), self.webSocket.subprotocol()))
        self.webSocket.sendTextMessage('{"action":"sub","channel":"killstream"}')
        if self.reconnectTimer.isActive():
            self.reconnectTimer.stop()

    def onClosed(self):
        self.status_kill_mail.emit(False)
        logging.info("Websocket closed from url {}".format(self.address))
        self.reconnectTimer.start()

    @staticmethod
    def _writeUTF16BOM(fp, txt):
        fp.write(UTF16_BOM + txt)

    @staticmethod
    def _writeHeader():
        if not os.path.exists(ZKillMonitor.MONITORING_PATH):
            with open(ZKillMonitor.MONITORING_PATH, "wt", encoding="utf-16-le") as fp:
                ZKillMonitor._writeUTF16BOM(fp, u'\n')
                ZKillMonitor._writeUTF16BOM(fp, u'\n')
                ZKillMonitor._writeUTF16BOM(fp, u'\n')
                ZKillMonitor._writeUTF16BOM(fp, u"---------------------------------------------------------------\n")
                ZKillMonitor._writeUTF16BOM(fp, u"Channel ID: zKillboard\n")
                ZKillMonitor._writeUTF16BOM(fp, u"Channel Name: zKillboard\n")
                ZKillMonitor._writeUTF16BOM(fp, u"---------------------------------------------------------------\n")
                ZKillMonitor._writeUTF16BOM(fp, u"Websocket listen to url wss://zkillboard.com/websocket/\n")
                ZKillMonitor._writeUTF16BOM(fp, u"---------------------------------------------------------------\n")
                ZKillMonitor._writeUTF16BOM(fp, u"\n")
                ZKillMonitor._writeUTF16BOM(fp, u"\n")
                ZKillMonitor._writeUTF16BOM(fp, u"\n")

    def onNewTextMessage(self, text):
        """
            callback for a new message
        Args:
            text: text received via websocket
        Returns:
            None
        """
        kill_data = json.loads(text)
        self.report_system_kill.emit(kill_data["solar_system_id"])
        self.logKillMail(kill_data)
        if self.logKillAsIntel(kill_data):
            kill_string = self.getIntelString(kill_data)
            self._writeHeader()
            with open(ZKillMonitor.MONITORING_PATH, "at", encoding='utf-16-le') as fp:
                ZKillMonitor._writeUTF16BOM(fp, kill_string)

    @staticmethod
    def logKillMail(kill_data):
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
    def getIntelString(kill_data) -> str:
        """
            gets the log text from teh json kill

        Args:
            kill_data: dict of kill

        Returns:
            log formatted text related to the kill dict
        """
        victim = kill_data["victim"]
        zk_time = kill_data["killmail_time"]
        system_id = kill_data["solar_system_id"]
        kill_url = kill_data["zkb"]["url"]

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
        total_value = "<br/>Total Value : {:,} ISK".format(
            kill_data["zkb"]["totalValue"]) if "totalValue" in kill_data["zkb"].keys() else ""

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
            ship=CTX.FORMAT_SHIP.format(kill_victim_ship_type),
            link=CTX.FORMAT_URL.format(kill_url),
            value=CTX.FORMAT_VALUE.format(total_value)
        )

    @staticmethod
    def updateKillDatabase(kill_data):
        victim = kill_data["victim"]
        alliance_id = victim["alliance_id"] if "alliance_id" in victim.keys() else 0
        return alliance_id in Cache().getAllianceBlue()

    @staticmethod
    def logKillAsIntel(kill_data) -> bool:
        """
        evaluates the kill to get a decision if the related message should be logged or not
        Args:
            kill_data: kill to be analyzed

        Returns:
            True if to be logged else False
        """
        blue_alliances = Cache().getAllianceBlue()
        if ZKillMonitor.LOG_VICTIM:
            victim = kill_data["victim"]
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
