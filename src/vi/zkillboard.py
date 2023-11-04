import datetime
import json
import logging
import os.path
import time

from PySide6.QtCore import QUrl, QObject, QTimer
from PySide6.QtWebSockets import QWebSocket, QWebSocketProtocol
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal as pyqtSignal

from vi.universe import Universe
from vi.chatparser.message import Message
import vi.evegate as evegate
from vi.cache import Cache
from vi.chatparser.ctx import CTX

# see https://github.com/zKillboard/zKillboard/wiki

class zkillMonitor(QObject):
    new_killmail = pyqtSignal(Message)
    MONITORING_PATH = "zkillMonitor.log"
    LOG_VICTIM = True
    LOG_ATTACKES = False
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
        logging.info("Websocket reconnecting to url {}".format(self.address))
        self.webSocket.open(QUrl(self.address))

    def startConnect(self):
        return
        self.reconnectTimer.stop()
        logging.info("Websocket connecting to url {}".format(self.address))
        self.webSocket.open(QUrl(self.address))

    def startDisconnect(self):
        logging.info("Websocket disconnecting from url {}".format(self.address))
        if self.reconnectTimer.isActive():
            self.reconnectTimer.stop()
        self.webSocket.close()

    def onError(self):
        logging.error("Websocket  error {} url: {}".format(self.webSocket.errorString(), self.address))

    def onConnected(self):
        logging.info("Websocket connected to url {}".format(self.address))
        self.webSocket.sendTextMessage('{"action":"sub","channel":"killstream"}')
        if self.reconnectTimer.isActive():
            self.reconnectTimer.stop()

    def onClosed(self):
        logging.info("Websocket closed from url {}".format(self.address))
        self.reconnectTimer.start()

    @staticmethod
    def _writeHeader():
        if not os.path.exists(zkillMonitor.MONITORING_PATH):
            with open(zkillMonitor.MONITORING_PATH, "w", encoding='utf-16-le') as fp:
                fp.write("\n")
                fp.write("\n")
                fp.write("\n")
                fp.write("---------------------------------------------------------------\n")
                fp.write("Channel ID: zKillboard\n")
                fp.write("Channel Name: zKillboard\n")
                fp.write("---------------------------------------------------------------\n")
                fp.write("Websocket listen to url wss://zkillboard.com/websocket/\n")
                fp.write("---------------------------------------------------------------\n")
                fp.write("\n")
                fp.write("\n")
                fp.write("\n")

    def onNewTextMessage(self, text):
        """
            callback for a new message
        Args:
            text: text received via websocket
        Returns:
            None
        """
        kill_data = json.loads(text)
        self.logKillmail(kill_data)
        if self.logKillAsIntel(kill_data):
            kill_string = self.getIntelString(kill_data)
            self._writeHeader()
            with open(zkillMonitor.MONITORING_PATH, "a", encoding='utf-16-le') as fp:
                fp.write(kill_string)

    @staticmethod
    def logKillmail(kill_data):
        kill_time = time.mktime(time.strptime(kill_data["killmail_time"], "%Y-%m-%dT%H:%M:%SZ"))
        Cache().putKillmailtoCache(
            killmail_id=kill_data["killmail_id"],
            region_id=Universe.regionIDFromSystemID(kill_data["solar_system_id"]),
            system_id=kill_data["solar_system_id"],
            modified=kill_time,
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
        victim      = kill_data["victim"]
        zTime       = kill_data["killmail_time"]
        system_id   = kill_data["solar_system_id"]
        kill_url    = kill_data["zkb"]["url"]
        atackers    = kill_data["attackers"]

        #  0---------1--------"
        #  0123456789012345678"
        #  2023.05.26 19:08:11"
        #  2023-10-22T07:53:16Z"

        kill_time = "{}.{}.{} {}".format(zTime[0:4],zTime[5:7],zTime[8:10],zTime[11:19])

        character_id = victim["character_id"] if "character_id" in victim.keys() else 0
        ship_type_id = victim["ship_type_id"] if "ship_type_id" in victim.keys() else 0
        alliance_id = victim["alliance_id"] if "alliance_id" in victim.keys() else 0
        user_data = evegate.esiUniverseNames([character_id, system_id, ship_type_id, alliance_id])

        kill_victim_character = user_data[character_id] if character_id and character_id in user_data.keys() else "-"
        kill_victim_ship_type = user_data[ship_type_id] if ship_type_id and ship_type_id in user_data.keys() else "-"
        kill_victim_alliance = user_data[alliance_id] if alliance_id and alliance_id in user_data.keys() else "-"
        kill_system_name = Universe.systemNameById(system_id)
        alliance_ticker = ""
        if alliance_id:
            message_msk = "[ {date} ] zKillboard.com >{link}<br/>{system} {player} &lt;{ticker}&gt; ({alliance}) lost a {ship}\n"
            alliance_ticker = evegate.esiAlliances(alliance_id)["ticker"]
        else:
            message_msk = "[ {date} ] zKillboard.com >{link}<br/>{system} {player} lost a {ship}\n"

        return(message_msk.format(
            date=kill_time,
            system=" {} ".format(kill_system_name),
            ticker=alliance_ticker,
            player=CTX.FORMAT_PLAYER_NAME.format(kill_victim_character, character_id),
            alliance=CTX.FORMAT_ALLIANCE_NAME.format(kill_victim_alliance, alliance_id),
            ship=CTX.FORMAT_SHIP.format(kill_victim_ship_type),
            link=CTX.FORMAT_URL.format(kill_url)))

    @staticmethod
    def updateKillDatabase(kill_data):
        victim = kill_data["victim"]
        character_id = victim["character_id"] if "character_id" in victim.keys() else 0
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
        if zkillMonitor.LOG_VICTIM:
            victim = kill_data["victim"]
            if "character_id" in victim.keys():
                character_id = victim["character_id"]
                if "alliance_id" in victim.keys():
                    alliance_id = victim["alliance_id"]
                    if alliance_id in blue_alliances:
                        return True

        if zkillMonitor.LOG_ATTACKES:
            for attacker in kill_data["attackers"]:
                if "alliance_id" in attacker.keys():
                    alliance_id = attacker["alliance_id"]
                    if alliance_id in blue_alliances:
                        return True

        return False


# The main application for testing
if __name__ == "__main__":
    appl = QApplication()
    mon = zkillMonitor(appl)
    #mon.startDisconnect()
    #mon.startConnect()
    Cache.PATH_TO_CACHE = "/home/jkeymer/Documents/EVE/spyglass/cache-2.sqlite3"
    for res in Cache().getKillmails():
        mon.onNewTextMessage(res)

    mon.onNewTextMessage(    '{"attackers":[{"alliance_id":99011426,"character_id":2113800353,"corporation_id":2042491468,"damage_done":2121,"faction_id":500001,"final_blow":true,"security_status":2.3,"ship_type_id":32876,"weapon_type_id":24471}],"killmail_id":111568833,"killmail_time":"2023-09-10T19:13:11Z","solar_system_id":30003838,"victim":{"character_id":891805972,"corporation_id":98649272,"damage_taken":2121,"faction_id":500004,"items":[{"flag":92,"item_type_id":31274,"quantity_destroyed":1,"singleton":0},{"flag":13,"item_type_id":28668,"quantity_destroyed":7,"singleton":0},{"flag":21,"item_type_id":29015,"quantity_dropped":1,"singleton":0},{"flag":11,"item_type_id":11351,"quantity_destroyed":1,"singleton":0},{"flag":93,"item_type_id":31274,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":29013,"quantity_dropped":3,"singleton":0},{"flag":20,"item_type_id":29015,"quantity_dropped":1,"singleton":0},{"flag":20,"item_type_id":5302,"quantity_dropped":1,"singleton":0},{"flag":94,"item_type_id":31262,"quantity_destroyed":1,"singleton":0},{"flag":21,"item_type_id":5302,"quantity_destroyed":1,"singleton":0},{"flag":12,"item_type_id":2048,"quantity_destroyed":1,"singleton":0},{"flag":22,"item_type_id":29015,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":28668,"quantity_dropped":35,"singleton":0},{"flag":22,"item_type_id":5302,"quantity_destroyed":1,"singleton":0},{"flag":87,"item_type_id":2488,"quantity_destroyed":1,"singleton":0},{"flag":87,"item_type_id":2488,"quantity_dropped":1,"singleton":0},{"flag":13,"item_type_id":33076,"quantity_destroyed":1,"singleton":0},{"flag":19,"item_type_id":35658,"quantity_destroyed":1,"singleton":0},{"flag":27,"item_type_id":23527,"quantity_dropped":1,"singleton":0}],"position":{"x":50249064688.9718,"y":98740481507.64902,"z":-103812962325.80627},"ship_type_id":609},"zkb":{"locationID":40242882,"hash":"b2f88d47a42180417cfb4fb6012d5d2439833385","fittedValue":2052113.47,"droppedValue":2113292.62,"destroyedValue":1855545.31,"totalValue":3968837.93,"points":10,"npc":false,"solo":true,"awox":false,"esi":"https:\/\/esi.evetech.net\/latest\/killmails\/111568833\/b2f88d47a42180417cfb4fb6012d5d2439833385\/","url":"https:\/\/zkillboard.com\/kill\/111568833\/"}}')
    mon.onNewTextMessage(    '{"attackers":[{"alliance_id":1354830081,"character_id":2118732338,"corporation_id":272675225,"damage_done":13334,"final_blow":true,"security_status":3.2,"ship_type_id":54733,"weapon_type_id":54753},{"alliance_id":1354830081,"character_id":2121654176,"corporation_id":272675225,"damage_done":9363,"final_blow":false,"security_status":3.2,"ship_type_id":54733,"weapon_type_id":54733},{"alliance_id":1354830081,"character_id":94852702,"corporation_id":272675225,"damage_done":9363,"final_blow":false,"security_status":5,"ship_type_id":54733,"weapon_type_id":54733},{"alliance_id":1354830081,"character_id":2119549805,"corporation_id":272675225,"damage_done":6242,"final_blow":false,"security_status":3.3,"ship_type_id":54733,"weapon_type_id":54733},{"alliance_id":1354830081,"character_id":2121654060,"corporation_id":272675225,"damage_done":5625,"final_blow":false,"security_status":3.3,"ship_type_id":33472,"weapon_type_id":33472}],"killmail_id":112630100,"killmail_time":"2023-10-26T18:44:41Z","solar_system_id":30004029,"victim":{"alliance_id":1354830081,"character_id":2114974539,"corporation_id":1599371034,"damage_taken":43927,"items":[{"flag":5,"item_type_id":5405,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":4871,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":249,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":6160,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":5955,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":8175,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":5141,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":9772,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":15331,"quantity_destroyed":3,"singleton":0},{"flag":5,"item_type_id":15331,"quantity_dropped":2,"singleton":0},{"flag":5,"item_type_id":11325,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":4435,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":5975,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":5973,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":4613,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":11343,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":239,"quantity_destroyed":1,"singleton":0},{"flag":5,"item_type_id":239,"quantity_dropped":1,"singleton":0}],"position":{"x":-1297750436059.8801,"y":-107863079470.15277,"z":752792375291.1194},"ship_type_id":33475},"zkb":{"locationID":40255179,"hash":"13160e17547460d12c3e7dafb9c5b0d41da8210e","fittedValue":11022666.67,"droppedValue":1839956.56,"destroyedValue":11098210.61,"totalValue":12938167.17,"points":1,"npc":false,"solo":false,"awox":false,"esi":"https:\/\/esi.evetech.net\/latest\/killmails\/112630100\/13160e17547460d12c3e7dafb9c5b0d41da8210e\/","url":"https:\/\/zkillboard.com\/kill\/112630100\/"}}' )
    mon.onNewTextMessage(    '{"attackers":[{"alliance_id":99012403,"character_id":705943331,"corporation_id":98667899,"damage_done":10516,"final_blow":true,"security_status":0.8,"ship_type_id":12005,"weapon_type_id":2446}],"killmail_id":112630116,"killmail_time":"2023-10-26T18:45:21Z","solar_system_id":30002702,"victim":{"alliance_id":1900696668,"character_id":2120580029,"corporation_id":98457033,"damage_taken":10516,"items":[{"flag":5,"item_type_id":33474,"quantity_dropped":1,"singleton":0},{"flag":31,"item_type_id":27441,"quantity_dropped":17,"singleton":0},{"flag":28,"item_type_id":27441,"quantity_destroyed":17,"singleton":0},{"flag":5,"item_type_id":27441,"quantity_dropped":1300,"singleton":0},{"flag":30,"item_type_id":2410,"quantity_destroyed":1,"singleton":0},{"flag":20,"item_type_id":3841,"quantity_dropped":1,"singleton":0},{"flag":25,"item_type_id":20199,"quantity_dropped":1,"singleton":0},{"flag":19,"item_type_id":20199,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":30488,"quantity_dropped":8,"singleton":0},{"flag":24,"item_type_id":19215,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":4258,"quantity_dropped":1,"singleton":0},{"flag":11,"item_type_id":25563,"quantity_dropped":1,"singleton":0},{"flag":29,"item_type_id":2410,"quantity_dropped":1,"singleton":0},{"flag":21,"item_type_id":20199,"quantity_dropped":1,"singleton":0},{"flag":12,"item_type_id":25563,"quantity_dropped":1,"singleton":0},{"flag":31,"item_type_id":2410,"quantity_dropped":1,"singleton":0},{"flag":30,"item_type_id":27441,"quantity_dropped":17,"singleton":0},{"flag":92,"item_type_id":31306,"quantity_destroyed":1,"singleton":0},{"flag":22,"item_type_id":3841,"quantity_dropped":1,"singleton":0},{"flag":27,"item_type_id":2410,"quantity_dropped":1,"singleton":0},{"flag":5,"item_type_id":2629,"quantity_dropped":1700,"singleton":0},{"flag":28,"item_type_id":2410,"quantity_dropped":1,"singleton":0},{"flag":29,"item_type_id":27441,"quantity_destroyed":17,"singleton":0},{"flag":93,"item_type_id":31306,"quantity_destroyed":1,"singleton":0},{"flag":23,"item_type_id":12058,"quantity_dropped":1,"singleton":0},{"flag":13,"item_type_id":25563,"quantity_dropped":1,"singleton":0},{"flag":27,"item_type_id":27441,"quantity_dropped":17,"singleton":0}],"position":{"x":-357956298552.59827,"y":-634567995055.7051,"z":738896037953.3048},"ship_type_id":11959},"zkb":{"locationID":40171923,"hash":"b7603dc963ffe3058377902025ebb9805330974f","fittedValue":256629115.18,"droppedValue":56364681.37,"destroyedValue":209359875.81,"totalValue":265724557.18,"points":58,"npc":false,"solo":true,"awox":false,"esi":"https:\/\/esi.evetech.net\/latest\/killmails\/112630116\/b7603dc963ffe3058377902025ebb9805330974f\/","url":"https:\/\/zkillboard.com\/kill\/112630116\/"}}')
    while True:
        appl.processEvents()
