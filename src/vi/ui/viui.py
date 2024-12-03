###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#   																	  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#                                                                         #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#   				                                                      #
#   				                                                      #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import json
import os
import datetime
import time
import requests
import parse

from typing import Optional

import logging
from PySide6.QtGui import Qt
from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtCore import QPoint, QPointF, QRectF, QSortFilterProxyModel, QTimer, Qt
from PySide6.QtCore import Signal
from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (QMessageBox, QFileDialog, QApplication, QAbstractItemView)

import vi.version
from vi.universe import Universe
from vi.system import System
from vi import evegate
from vi import dotlan, filewatcher
from vi.states import States
from vi.globals import Globals
from vi.ui import JumpbridgeChooser, ChatroomChooser, SystemChat, ChatEntryWidget, ChatEntryItem

from vi.cache.cache import Cache, currentEveTime
from vi.resources import resourcePath, resourcePathExists
from vi.soundmanager import SoundManager
from vi.threads import AvatarFindThread, MapStatisticsThread, STAT
from vi.redoundoqueue import RedoUndoQueue
from vi.ui.systemtray import JumpBridgeContextMenu
from vi.ui.systemtray import MapContextMenu
from vi.ui.systemtray import POIContextMenu
from vi.ui.systemtray import TheraContextMenu
from vi.ui.systemtray import ActionPackage
from vi.ui.styles import Styles
from vi.chatparser.chatparser import ChatParser
from vi.clipboard import evaluateClipboardData, tokenize_eve_formatted_text
from vi.ui.modelplayer import TableModelPlayers, StyledItemDelegatePlayers
from vi.ui.modelthera import TableModelThera
from vi.ui.modelstorm import TableModelStorm
from vi.ui.modelpoi import POITableModel, StyledItemDelegatePOI

from vi.universe.routeplanner import RoutPlanner

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtSql import QSqlQueryModel

from vi.ui import Ui_MainWindow, Ui_EVESpyInfo, Ui_SoundSetup

from vi.chatparser.message import Message, CTX

from vi.zkillboard import ZKillMonitor

from vi.system import ALL_SYSTEMS

"""
 Timer intervals
"""
MAP_UPDATE_INTERVAL_MSEC = 20
CLIPBOARD_CHECK_INTERVAL_MSEC = 125

# todo: move threads to sep object


class MainWindow(QtWidgets.QMainWindow):

    chat_message_added = Signal(object, object)
    avatar_loaded = Signal(object, object)
    jbs_changed = Signal()
    players_changed = Signal()
    poi_changed = Signal()
    region_changed_by_system_id = Signal(int)
    region_changed = Signal(str)
    current_system_changed = Signal(str)

    def _update_splash_window_info(self, string):
        if self._update_splash:
            self._update_splash(string)

    @staticmethod
    def _initialChatRoomsFromCache(cache):
        cached_room_name = cache.getFromCache("room_names")
        if cached_room_name:
            cached_room_name = cached_room_name.split(",")
        else:
            cached_room_name = ChatroomChooser.DEFAULT_ROOM_MANES
            cache.putIntoCache("room_names", u",".join(cached_room_name), 60 * 60 * 24 * 365 * 5)
        return cached_room_name

    def __init__(self, pat_to_logfile, update_splash=None):
        QtWidgets.QMainWindow.__init__(self)
        self._update_splash = update_splash
        self._update_splash_window_info("Init GUI application")
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(
            "EVE-Spy " + vi.version.VERSION + "{dev}".format(dev="-SNAPSHOT" if vi.version.SNAPSHOT else ""))
        self.cache = Cache()
        self.region_queue = RedoUndoQueue()
        self.pathToLogs = pat_to_logfile
        self.mapPositionsDict = {}
        self.mapStatisticCache = {}
        self.oldClipboardContent = ""
        self.autoChangeRegion = False
        self.room_names = self._initialChatRoomsFromCache(self.cache)
        self.currentSystem = None

        self._update_splash_window_info("Update chat parser")
        self.chatparser = ChatParser(self.pathToLogs, self.room_names)

        self._update_splash_window_info("Setup worker threads")
        self.apiThread = None   # thread used for api registration
        self.avatarFindThread = None  # avatar find thread
        self.filewatcherThread = None   # the file watcher
        self.statisticsThread = None  # map statistic thread
        self.zkillboard = None  # zKillBoard monitor
        self._setupThreads()
        self.curr_region_name = self.cache.getFromCache("region_name")
        self.dotlan = self.setupRegionMap(self.curr_region_name)
        self.mapTimer = QTimer(self)
        self.mapTimer.timeout.connect(self.updateMapView)

        self.completer_system_names = QtWidgets.QCompleter(Universe.systemNames())
        self.completer_system_names.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer_system_names.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.ui.systemNames.setCompleter(self.completer_system_names)

        self.ui.systemNames.inputRejected.connect(lambda: self.ui.systemNames.hide())
        self.ui.systemNames.editingFinished.connect(lambda: (
            self.ui.searchSystem.setChecked(False),
            self.changeRegionBySystemID(Universe.systemIdByName(system_name=self.ui.systemNames.text())),
            self.markSystemOnMap(self.ui.systemNames.text()),
            ))
        self.ui.systemNames.hide()

        # add completer system names
        icon = QIcon()
        icon.addPixmap(QtGui.QPixmap(u":/Icons/res/eve-sso-login-black-small.png"), QIcon.Normal, QIcon.Off)
        icon.addPixmap(QtGui.QPixmap(u":/Icons/res/eve-sso-login-black-small.png"), QIcon.Normal, QIcon.On)
        self.ui.connectToEveOnline.setIcon(icon)
        self.ui.connectToEveOnline.setIconSize(QtCore.QSize(163, 38))
        self.ui.connectToEveOnline.setFlat(False)

        self.window_icon = QIcon(":/Icons/res/icon.ico")
        self.setWindowIcon(self.window_icon)
        self.setFocusPolicy(Qt.StrongFocus)

        self.clipboard = QApplication.clipboard()
        self.alarmDistance = 0
        self.chatEntries = []
        self.ui.frameButton.setVisible(False)
        self.initialMapPosition = None
        self.invertWheel = False
        self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint| Qt.WindowSystemMenuHint)
        try:
            status = evegate.esiStatus()
            info = "Server ({server_version}) online {players} players started {start_time}.".format(**status)
            logging.info(info)
            self._update_splash_window_info(info)
        except (Exception,) as _:
            self._update_splash_window_info("There was no response from the server, perhaps the server is down.")

        self._update_splash_window_info("Fetch universe system jumps via ESI.")
        self._update_splash_window_info("Fetch player sovereignty via ESI.")
        self._update_splash_window_info("Fetch incursions via ESI...")
        self._update_splash_window_info("Fetch sovereignty campaigns via ESI...")

        self._connectActionPack()

        self._update_splash_window_info("Preset application")

        self._update_splash_window_info("Set up Theme menu - fill in list of themes and add connections")
        self.themeGroup = QActionGroup(self.ui.menu)
        styles = Styles()
        for theme in styles.getStyles():
            action = QAction(theme, None)
            action.setCheckable(True)
            action.theme = theme
            if action.theme == styles.currentStyle:
                action.setChecked(True)
            logging.info("Adding theme {}".format(theme))
            action.triggered.connect(self.changeTheme)
            self.themeGroup.addAction(action)
            self.ui.menuTheme.addAction(action)

        # Load user's toon names
        for api_char_names in self.cache.getAPICharNames():
            if evegate.esiCharactersOnline(api_char_names):
                self._updateKnownPlayerAndMenu(api_char_names)

        self._updateKnownPlayerAndMenu(None)
        self._update_splash_window_info("Update player names")
        # Set up Theme menu - fill in list of themes and add connections

        if self.invertWheel is None:
            self.invertWheel = False

        self.ui.actionInvertMouseWheel.setChecked(self.invertWheel)
        self._addPlayerMenu()
        self.players_changed.connect(self._addPlayerMenu)

        # Set up user's intel rooms
        self._update_splash_window_info("Set up user's intel rooms")

        # Disable the sound UI if sound is not available
        self._update_splash_window_info("Doublecheck the sound UI if sound is not available...")
        if not SoundManager.soundAvailable:
            self.changeSound(disable=True)
            self._update_splash_window_info("Sound disabled.")
        else:
            self.changeSound()
            self._update_splash_window_info("Sound successfully enabled.")

        # Set up Transparency menu - fill in opacity values and make connections
        self._update_splash_window_info("Set up Transparency menu - fill in opacity values and make connections")

        self.ui.actionOpacity_100.triggered.connect(lambda: self.changeWindowOpacity(1.0))
        self.ui.actionOpacity_80.triggered.connect(lambda: self.changeWindowOpacity(0.8))
        self.ui.actionOpacity_60.triggered.connect(lambda: self.changeWindowOpacity(0.6))
        self.ui.actionOpacity_40.triggered.connect(lambda: self.changeWindowOpacity(0.4))
        self.ui.actionOpacity_20.triggered.connect(lambda: self.changeWindowOpacity(0.2))
        self.ui.updateAvail.hide()
        self._updateWindowOpacityActions(self.windowOpacity())

        self._update_splash_window_info("Setup UI")
        self._wireUpUIConnections()
        self._update_splash_window_info("Recall cached settings")

        self._startStatisticTimer()
        self._update_splash_window_info("Fetch data from eve-scout.com")
        self._wireUpDatabaseViews()

        self._update_splash_window_info("Start all worker threads")
        self._recallCachedSettings()
        self._startThreads()

        self._update_splash_window_info("Apply theme.")

        initial_theme = self.cache.getFromCache("theme")
        if initial_theme:
            self.changeTheme(initial_theme)

        self._update_splash_window_info("EVE-Syp perform an initial scan of all intel files.")
        self.rescanIntel()
        self.tool_widget = None

        self._update_splash_window_info("EVE-Syp preparing the map view.")
        self.updateMapView()
        self._update_splash_window_info("Initialisation succeeded.")

    def checkForUpdate(self, update_avail):
        if update_avail[0]:
            logging.info(update_avail[1])
            self.ui.updateAvail.show()
            self.ui.updateAvail.setText(update_avail[1])

            def openDownloadLink():
                QDesktopServices.openUrl(evegate.getSpyglassUpdateLink())
                self.ui.updateAvail.hide()
                self.ui.updateAvail.disconnect(openDownloadLink)
            self.ui.updateAvail.clicked.connect(openDownloadLink)
        else:
            logging.info(update_avail[1])
            self.ui.updateAvail.hide()

    def showStatistic(self) -> bool:
        return self.ui.actionShowSystemStatisticOnMap.isChecked()

    def setShowStatistic(self, val):
        if val != self.ui.actionShowSystemStatisticOnMap.isChecked():
            self.ui.actionShowSystemStatisticOnMap.setChecked(val)

    def showJumpbridge(self) -> bool:
        return self.ui.actionShowJumpBridgeConnectionsOnMap.isChecked()

    def setShowJumpbridge(self, value):
        if value != self.ui.actionShowJumpBridgeConnectionsOnMap.isChecked():
            self.ui.actionShowJumpBridgeConnectionsOnMap.setChecked(value)

    def showADMOnMap(self) -> bool:
        return self.ui.actionShowADMonMap.isChecked()

    def setShowADMOnMap(self, val) -> None:
        self.ui.actionShowADMonMap.setChecked(val)

    def useThreaRoutes(self):
        self.ui.actionUserTheraRoutes.isChecked()

    def setUseThreaRoutes(self, val) -> None:
        self.ui.actionUserTheraRoutes.setChecked(val)

    @property
    def showAvatar(self) -> bool:
        return self.ui.actionShowChatAvatars.isChecked()

    @showAvatar.setter
    def showAvatar(self, val) -> None:
        self.ui.actionShowChatAvatars.setChecked(val)

    @property
    def systems_on_map(self) -> dict[str, System]:
        return self.dotlan.systems

    @property
    def systemsById(self) -> dict[int, System]:
        return self.dotlan.systemsById

    @property
    def systemsByName(self) -> dict[str, System]:
        return self.dotlan.systemsByName

    @property
    def monitoredPlayerNames(self):
        return self.cache.getActivePlayerNames()

    @property
    def knownPlayerNames(self):
        return self.cache.getKnownPlayerNames()

    def show(self):
        QtWidgets.QMainWindow.show(self)

    def _connectActionPack(self):
        self.actions_pack = ActionPackage()

    def _updateKnownPlayerAndMenu(self, names=None):
        """
        Updates the players menu
        Args:
            names:

        Returns:

        """
        known_player_names = self.knownPlayerNames
        chars_registered = len(known_player_names) != 0
        self.ui.apiCharLabel.setVisible(chars_registered)
        self.ui.currentESICharacter.setVisible(chars_registered)
        self.ui.locateChar.setVisible(chars_registered)

        if names is None:
            self.players_changed.emit()
        elif isinstance(names, str):
            if names not in known_player_names:
                known_player_names.add(names)
        else:
            for name in names:
                if name not in known_player_names:
                    known_player_names.add(name)

        if known_player_names != self.knownPlayerNames:
            self.cache.setKnownPlayerNames(known_player_names)
            self.players_changed.emit()

    def _addPlayerMenu(self):
        self.playerGroup = QActionGroup(self.ui.menu)
        self.playerGroup.setExclusionPolicy(QActionGroup.ExclusionPolicy.None_)
        self.ui.menuChars.clear()
        for name in self.knownPlayerNames:
            action = QAction(name)
            action.setCheckable(True)
            action.playerName = name
            action.playerUse = name in self.monitoredPlayerNames
            action.setChecked(action.playerUse)
            action.setIconVisibleInMenu(action.playerUse)
            action.triggered.connect(self.changeMonitoredPlayerNamesFromMenu)
            self.playerGroup.addAction(action)
            self.ui.menuChars.addAction(action)

    def changeMonitoredPlayerNamesFromMenu(self):
        """
            Updates the monitoredPlayerNames set from the menu

        Returns:
            None
        """
        player_used = set()
        for action in self.playerGroup.actions():
            action.setIconVisibleInMenu(action.isChecked())
            if action.isChecked():
                player_used.add(action.playerName)
        self.cache.setActivePlayerNames(player_used)
        self.players_changed.emit()

    @Slot(bool)
    def changeInvertMouseWheel(self, checked):
        self.invertWheel = checked
        if self.invertWheel:
            self.ui.mapView.wheel_dir = -1.0
        else:
            self.ui.mapView.wheel_dir = 1.0
        self.ui.actionInvertMouseWheel.setChecked(self.invertWheel)

    def _recallCachedSettings(self):
        try:
            self.cache.recallAndApplySettings(self, "settings")
        except (Exception,) as e:
            logging.error(e)

    @Slot()
    def addNewESICharacter(self):
        if evegate.openWithEveonline(parent=self):
            self._updateKnownPlayerAndMenu(None)
            last_char_name = evegate.esiCharName()
            self.ui.currentESICharacter.clear()
            self.ui.currentESICharacter.addItems(self.cache.getAPICharNames())
            self.ui.currentESICharacter.setCurrentText(last_char_name)

    def selectESIChar(self, character_name):
        evegate.setEsiCharName(character_name)
        self.statisticsThread.fetchLocation(fetch=True)
        # self.rescanIntel()
        self.players_changed.emit()

    def regionNameChanged(self, new_region_name):
        if hasattr(self, "statisticsThread"):
            self.statisticsThread.fetchLocation(fetch=False)
        if new_region_name in [region["name"] for region in Universe.REGIONS]:
            self.changeRegionByName(region_name=new_region_name)

    @Slot(float)
    def updateX(self, x: float):
        pos = self.ui.mapView.scrollPosition()
        if pos.x != x:
            pos.setX(x)
            self.ui.mapView.setScrollPosition(pos)
            self.ui.mapView.update()

    @Slot(float)
    def updateY(self, y: float):
        pos = self.ui.mapView.scrollPosition()
        if pos.y != y:
            pos.setY(y)
            self.ui.mapView.setScrollPosition(pos)
            self.ui.mapView.update()

    @Slot(bool)
    def mapviewIsScrolling(self, scrolled_active):
        if scrolled_active:
            self.mapTimer.stop()
        else:
            curr_pos = self.ui.mapView.scrollPosition()
            curr_zoom = self.ui.mapView.zoomFactor()
            self.region_queue.enqueue((self.curr_region_name, curr_pos, curr_zoom))
            self.mapTimer.start(MAP_UPDATE_INTERVAL_MSEC)

    def _wireUpUIConnections(self):
        logging.info("wireUpUIConnections")
        self.ui.frameButton.setDefaultAction(self.ui.actionFramelessWindow)
        self.ui.showAvatar.setDefaultAction(self.ui.actionShowChatAvatars)
        self.ui.adm_vul_Button.setDefaultAction(self.ui.actionShowADMonMap)
        self.ui.jumpbridgesButton.setDefaultAction(self.ui.actionShowJumpBridgeConnectionsOnMap)
        self.ui.statisticsButton.setDefaultAction(self.ui.actionShowSystemStatisticOnMap)
        self.ui.toolUseTheraRouting.setDefaultAction(self.ui.actionUserTheraRoutes)
        self.ui.autoCenterChar.setDefaultAction(self.ui.actionAutoSwitchRegions)

        self.clipboard.dataChanged.connect(self.clipboardChanged)
        self.ui.actionAlwaysOnTop.triggered.connect(self.changeAlwaysOnTop)
        self.ui.actionCatchRegion.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.actionCatchRegion))
        self.ui.actionProvidenceRegion.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.actionProvidenceRegion))
        self.ui.actionQueriousRegion.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.actionQueriousRegion))
        self.ui.actionProvidenceCatchRegion.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.actionProvidenceCatchRegion))
        self.ui.actionProvidenceCatchCompactRegion.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.actionProvidenceCatchCompactRegion))
        self.ui.actionWickedcreekScaldingpassRegion.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.actionWickedcreekScaldingpassRegion))

        self.ui.actionShowTabs.triggered.connect(self.changeChatVisibility)
        self.ui.actionSoundSetup.triggered.connect(self.showSoundSetup)
        self.ui.actionActivateSound.triggered.connect(self.changeSound)
        self.ui.actionUseSpokenNotifications.triggered.connect(self.changeUseSpokenNotifications)
        self.ui.actionFramelessWindow.triggered.connect(self.changeFrameless)
        self.ui.actionJumpbridgeData.triggered.connect(self.showJumpbridgeChooser)
        self.ui.actionRescanIntelNow.triggered.connect(self.rescanIntel)
        self.ui.actionClear_Intel_Chat.triggered.connect(self.clearIntelChat)
        self.ui.mapView.webViewUpdateScrollbars.connect(self.fixupScrollBars)
        self.ui.mapView.customContextMenuRequested.connect(self.showMapContextMenu)
        self.ui.regionNameField.addItems(sorted([region["name"] for region in Universe.REGIONS]))

        self.ui.mapView.webViewIsScrolling.connect(self.mapviewIsScrolling)
        self.ui.mapHorzScrollBar.valueChanged.connect(self.updateX)
        self.ui.mapVertScrollBar.valueChanged.connect(self.updateY)

        self.ui.actionOpen_on_dotlan.triggered.connect(lambda: QDesktopServices.openUrl(
            "https://evemaps.dotlan.net/system/{}".format(self.currentSystem.name)))

        self.ui.actionOpen_on_zKillboard.triggered.connect(lambda: QDesktopServices.openUrl(
            "https://zkillboard.com/system/{}".format(self.currentSystem.system_id)))

        self.ui.actionChange_Region_to.triggered.connect(lambda: self.changeRegionBySystemID(
            self.currentSystem.system_id))

        self.ui.actionAlarm_distance_0.triggered.connect(lambda: self.changeAlarmDistance(0))
        self.ui.actionAlarm_distance_1.triggered.connect(lambda: self.changeAlarmDistance(1))
        self.ui.actionAlarm_distance_2.triggered.connect(lambda: self.changeAlarmDistance(2))
        self.ui.actionAlarm_distance_3.triggered.connect(lambda: self.changeAlarmDistance(3))
        self.ui.actionAlarm_distance_4.triggered.connect(lambda: self.changeAlarmDistance(4))
        self.ui.actionAlarm_distance_5.triggered.connect(lambda: self.changeAlarmDistance(5))

        self.ui.actionIntel_Time_5_min.triggered.connect(lambda: self.changeIntelTime(5))
        self.ui.actionIntel_Time_10_min.triggered.connect(lambda: self.changeIntelTime(10))
        self.ui.actionIntel_Time_20_min.triggered.connect(lambda: self.changeIntelTime(20))
        self.ui.actionIntel_Time_30_min.triggered.connect(lambda: self.changeIntelTime(30))
        self.ui.actionIntel_Time_60_min.triggered.connect(lambda: self.changeIntelTime(60))

        def hoveCheck(global_pos: QPoint, pos: QPointF):
            """
                Figure out if a system is below the mouse position
                using QtWidgets.QToolTip to popup system relate information on screen
            Args:
                global_pos: global position
                pos: position related to the svg
            """
            system_hovered = False
            for system in self.systems_on_map.values():
                if system.mapCoordinates.contains(pos):
                    if not QtWidgets.QToolTip.isVisible():
                        QtWidgets.QToolTip.showText(global_pos, system.getTooltipText(), self)
                        QApplication.setOverrideCursor(Qt.PointingHandCursor)
                    system_hovered = True

            if not system_hovered and QApplication.overrideCursor() and QtWidgets.QToolTip.isVisible():
                QApplication.restoreOverrideCursor()
                QtWidgets.QToolTip.hideText()

        self.ui.mapView.hoveCheck = hoveCheck

        def doubleClicked(pos: QPoint):
            for name, system in self.systems_on_map.items():
                if system.mapCoordinates.contains(pos):
                    self.mapLinkClicked(QtCore.QUrl("map_link/{0}".format(name)))
                    break

        self.ui.mapView.webViewDoubleClicked.connect(doubleClicked)

    def handleDestinationActions(self, act, destination, jump_route=None) -> bool:
        """
        Handles the set destination functionality for a registered character, the destination dict
        Args:
            act: action to be used,needs the dict attribute eve_action with key "player_name"
            destination: at least one of the keys "system_id" or "solar_system_id", the keys "structure_id" and
                "station_id" are optional.
            jump_route:

        Returns:
            True if succeeded

        """
        if hasattr(act, "eve_action") or "player_name" in destination:
            if "system_id" in destination:
                system_id = destination["system_id"]
            elif "structure_id" in destination:
                system_id = destination["structure_id"]
            elif "solar_system_id" in destination:
                system_id = destination["solar_system_id"]
            else:
                return False
            if "player_name" in destination:
                player_name = destination["player_name"]
            else:
                player_name = act.eve_action["player_name"]
            if self.useThreaRoutes:
                evegate.ESAPIListPublicSignatures()
                the_route = RoutPlanner.findRoute(
                    src_id=evegate.esiCharactersLocation(player_name),
                    dst_id=system_id,
                    use_ansi=True,
                    use_thera=True
                )

                last_thera = False
                first = True
                last = len(the_route.attr)
                for way_point in the_route.attr:
                    last = last - 1
                    if (way_point["name"] != "Thera" and way_point["name"] != "Turnur" and way_point["type"] != "Thera"
                            and last > 0 and not last_thera):
                        continue

                    last_thera = way_point["name"] == "Thera" or way_point["name"] == "Turnur"

                    evegate.esiAutopilotWaypoint(
                        char_name=player_name,
                        system_id=way_point["node"],
                        clear_all=first,
                        beginning=first)
                    first = False

                if "station_id" in destination.keys():
                    evegate.esiAutopilotWaypoint(player_name, destination["station_id"],
                                                 beginning=False, clear_all=False)
                elif "structure_id" in destination.keys():
                    evegate.esiAutopilotWaypoint(player_name, destination["structure_id"],
                                                 beginning=False, clear_all=False)

                return True
            if act.eve_action["action"] == "destination":
                if "structure_id" in destination.keys():
                    evegate.esiAutopilotWaypoint(player_name, destination["structure_id"])
                    return True
                elif "station_id" in destination.keys():
                    evegate.esiAutopilotWaypoint(player_name, destination["station_id"])
                    return True
                else:
                    evegate.esiAutopilotWaypoint(player_name, system_id)
                    return True
            elif act.eve_action["action"] == "waypoint":
                evegate.esiAutopilotWaypoint(
                    char_name=player_name,
                    system_id=system_id,
                    clear_all=False,
                    beginning=False)
                return True
            elif act.eve_action["action"] == "clearall":
                player_location = evegate.esiCharactersLocation(player_name)
                if player_location:
                    evegate.esiAutopilotWaypoint(player_name, player_location)
                return True
            elif act.eve_action["action"] == "route":
                if jump_route is None:
                    evegate.esiAutopilotWaypoint(player_name, system_id)
                    return True
                else:
                    first = True
                    for way_point in jump_route:
                        evegate.esiAutopilotWaypoint(
                            char_name=evegate.esiCharName(),
                            system_id=way_point,
                            clear_all=first,
                            beginning=first)
                        first = False
                    return True

        return False

    def _wireUpDatabaseViews(self):
        self._wireUpDatabaseViewsJB()
        self._wireUpDatabaseViewPOI()
        self._wireUpDatabaseCharacters()
        self._wireUpThera()
        self._wireUpStorm()

    def _wireUpDatabaseViewPOI(self):
        model = POITableModel()

        def callPOIUpdate():
            model.setQuery("SELECT type as Type, name as Name FROM pointofinterest ORDER BY sid")
            self.ui.tableViewPOIs.resizeColumnsToContents()
            self.ui.tableViewPOIs.resizeRowsToContents()

        self.ui.tableViewPOIs.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.ui.tableViewPOIs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tableViewPOIs.setDragEnabled(True)
        self.ui.tableViewPOIs.setAcceptDrops(True)
        self.ui.tableViewPOIs.setDropIndicatorShown(True)
        self.ui.tableViewPOIs.setDragDropOverwriteMode(False)
        self.ui.tableViewPOIs.setDropIndicatorShown(True)
        self.ui.tableViewPOIs.setDefaultDropAction(Qt.MoveAction)
        # callPOIUpdate()
        self.tableViewPOIsDelegate = StyledItemDelegatePOI(self)
        model.poi_order_changed.connect(callPOIUpdate)
        self.tableViewPOIsDelegate.poi_edit_changed.connect(callPOIUpdate)
        self.ui.tableViewPOIs.setModel(model)
        self.ui.tableViewPOIs.setDragDropMode(QAbstractItemView.InternalMove)
        self.ui.tableViewPOIs.setItemDelegate(self.tableViewPOIsDelegate)
        self.ui.tableViewPOIs.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.ui.tableViewPOIs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tableViewPOIs.resizeColumnsToContents()
        self.ui.tableViewPOIs.resizeRowsToContents()
        self.poi_changed.connect(callPOIUpdate)
        self.ui.tableViewPOIs.show()
        callPOIUpdate()

        def showPOIContextMenu(pos):
            index = self.ui.tableViewPOIs.indexAt(pos).row()
            item = self.cache.getPOIAtIndex(index)
            system_id = None
            if "solar_system_id" in item:
                system_id = int(item["solar_system_id"])
            elif "sys" in item:
                system_id = Universe.systemIdByName(item["sys"])
            elif "system_id" in item:
                system_id = int(item["system_id"])

            if system_id is None:
                lps_ctx_menu = POIContextMenu()
            else:
                lps_ctx_menu = POIContextMenu(system_name=Universe.systemNameById(system_id))

            lps_ctx_menu.setStyleSheet(Styles.getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewPOIs.mapToGlobal(pos))
            if item and "destination_id" in item.keys():

                if self.handleDestinationActions(res, item):
                    return
                elif res == lps_ctx_menu.copy:
                    if "structure_id" in item.keys():
                        self.oldClipboardContent = "<url=showinfo:{}//{}>{}</url>".format(
                            item["type_id"], item["structure_id"], item["name"])
                        self.clipboard.setText(self.oldClipboardContent)
                    elif "station_id" in item.keys():
                        self.oldClipboardContent = "<url=showinfo:{}//{}>{}</url>".format(
                            item["type_id"], item["station_id"], item["name"])
                        self.clipboard.setText(self.oldClipboardContent)
                    return
                elif res == lps_ctx_menu.copy_all:
                    txt = str()
                    for item in self.cache.getPOIs():
                        if txt != "":
                            txt = txt + "\n"
                        if "structure_id" in item.keys():
                            txt = txt + "<url=showinfo:{}//{}>{}</url>".format(
                                item["type_id"], item["structure_id"], item["name"])
                        elif "station_id" in item.keys():
                            txt = txt + "<url=showinfo:{}//{}>{}</url>".format(
                                item["type_id"], item["station_id"], item["name"])
                    self.oldClipboardContent = txt
                    self.clipboard.setText(self.oldClipboardContent)
                    return
                elif res == lps_ctx_menu.delete:
                    self.cache.clearPOI(item["destination_id"])
                    self.poi_changed.emit()
                    return
                elif res == lps_ctx_menu.selectRegion:
                    if system_id is not None:
                        self.region_changed_by_system_id.emit(system_id)
                    return

        self.ui.tableViewPOIs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableViewPOIs.customContextMenuRequested.connect(showPOIContextMenu)

    @Slot(str)
    def changeTheraSystem(self, system_name):
        pass

    @Slot(str)
    def changeCurrentSystem(self, system_name):
        pass

    @Slot()
    def updateTheraConnections(self):
        self.statisticsThread.requestWormholes()

    @Slot()
    def updateObservationsRecords(self):
        self.statisticsThread.requestObservationsRecords()

    def setTheraConnections(self, connections):
        if self.dotlan:
            self.dotlan.setTheraConnections(connections)
        self.ui.tableViewThera.model().sourceModel().setTheraConnections(connections)

    @Slot()
    def theraSystemChanged(self):
        system_name = self.ui.lineEditThera.text()
        self.cache.putIntoCache("thera_source_system", system_name)
        self.statisticsThread.setCurrentTheraSystem(system_name)
        self.statisticsThread.requestWormholes()

    def _wireUpThera(self):
        str_list = QtWidgets.QCompleter(Universe.systemNames())
        str_list.setCaseSensitivity(Qt.CaseInsensitive)
        str_list.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)

        model = TableModelThera()
        sort = QSortFilterProxyModel()
        sort.setSourceModel(model)
        self.ui.tableViewThera.setModel(sort)
        self.ui.tableViewThera.horizontalHeader().setDragEnabled(True)
        self.ui.tableViewThera.horizontalHeader().setAcceptDrops(True)
        self.ui.tableViewThera.horizontalHeader().setDragDropMode(QAbstractItemView.DragDrop)
        self.ui.tableViewThera.horizontalHeader().setDefaultDropAction(Qt.MoveAction)
        self.ui.tableViewThera.horizontalHeader().setDragDropOverwriteMode(True)
        self.ui.tableViewThera.horizontalHeader().setDropIndicatorShown(True)

        self.ui.lineEditThera.setCompleter(str_list)

        system_name = self.cache.getFromCache("thera_source_system")
        if system_name:
            self.statisticsThread.setCurrentTheraSystem(system_name)
            self.ui.lineEditThera.setText(system_name)

        self.ui.lineEditThera.editingFinished.connect(self.theraSystemChanged)

        def showTheraContextMenu(pos):
            menu_inx = self.ui.tableViewThera.model().mapToSource(self.ui.tableViewThera.indexAt(pos))
            item = self.ui.tableViewThera.model().sourceModel().thera_data[menu_inx.row()]

            if menu_inx.column() == 8:
                target_system_name = item["out_system_name"]
            else:
                target_system_name = item["in_system_name"]

            lps_ctx_menu = TheraContextMenu(target_system_name)
            lps_ctx_menu.setStyleSheet(Styles.getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewThera.mapToGlobal(pos))
            if self.handleDestinationActions(
                    act=res, destination={"system_id": Universe.systemIdByName(target_system_name)}):
                return
            elif res == lps_ctx_menu.updateData:
                self.statisticsThread.requestWormholes()
                return
            elif res == lps_ctx_menu.selectRegion:
                self.region_changed_by_system_id.emit(Universe.systemIdByName(target_system_name))
                return

        self.ui.tableViewThera.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableViewThera.customContextMenuRequested.connect(showTheraContextMenu)

    def _wireUpDatabaseViewsJB(self):
        model = QSqlQueryModel()

        def callOnUpdate():
            if self.dotlan:
                self.dotlan.setJumpbridges(self.cache.getJumpGates())
            model.setQuery("SELECT (src||' » ' ||jumpbridge.dst)as 'Gate Information', " 
                           "datetime(modified,'unixepoch','localtime') as 'last update', "
                           "( case used when 2 then 'okay' else 'probably okay' END ) 'Paired' FROM jumpbridge")
        self.callOnJbUpdate = callOnUpdate
        callOnUpdate()
        self.jbs_changed.connect(callOnUpdate)
        sort = QSortFilterProxyModel()
        sort.setSourceModel(model)
        self.ui.tableViewJBs.setModel(sort)
        self.ui.tableViewJBs.show()

        def showJBContextMenu(pos):
            inx_selected = self.ui.tableViewJBs.selectedIndexes()
            items = dict()
            for inx in inx_selected:
                items[inx.row()] = self.cache.getJumpGatesAtIndex(inx.row())
            index = self.ui.tableViewJBs.model().mapToSource(self.ui.tableViewJBs.indexAt(pos)).row()
            item = self.cache.getJumpGatesAtIndex(index)
            if item:
                lps_ctx_menu = JumpBridgeContextMenu(item["src"], item["dst"])
            else:
                lps_ctx_menu = JumpBridgeContextMenu()

            lps_ctx_menu.setStyleSheet(Styles.getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewJBs.mapToGlobal(pos))
            source_id = item["id_src"] if item["id_src"] is not None else Universe.systemIdByName(item["src"])
            if self.handleDestinationActions(res, destination={"system_id": source_id}):
                return
            elif res == lps_ctx_menu.update:
                inx_selected = self.ui.tableViewJBs.selectedIndexes()
                items = dict()
                for inx in inx_selected:
                    items[inx.row()] = self.cache.getJumpGatesAtIndex(inx.row())
                for item in items.values():
                    evegate.getAllJumpGates(name_char=evegate.esiCharName(),
                                            system_name_src=item["src"],
                                            system_name_dst=item["dst"])
                    self.jbs_changed.emit()
                return
            elif res == lps_ctx_menu.delete:
                inx_selected = self.ui.tableViewJBs.selectedIndexes()
                items = dict()
                for inx in inx_selected:
                    items[inx.row()] = self.cache.getJumpGatesAtIndex(inx.row())
                for item in items.values():
                    self.cache.clearJumpGate(item["src"])
                    self.jbs_changed.emit()
                return
            elif res == lps_ctx_menu.selectRegionSrc:
                items = dict()
                inx_selected = self.ui.tableViewJBs.selectedIndexes()
                for inx in inx_selected:
                    items[inx.row()] = self.cache.getJumpGatesAtIndex(inx.row())
                for item in items.values():
                    if "src" in item:
                        self.region_changed_by_system_id.emit(Universe.systemIdByName(item["src"]))
                return
            elif res == lps_ctx_menu.selectRegionDst:
                items = dict()
                inx_selected = self.ui.tableViewJBs.selectedIndexes()
                for inx in inx_selected:
                    items[inx.row()] = self.cache.getJumpGatesAtIndex(inx.row())
                for item in items.values():
                    if "dst" in item:
                        self.region_changed_by_system_id.emit(Universe.systemIdByName(item["dst"]))
                return
        self.ui.tableViewJBs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableViewJBs.customContextMenuRequested.connect(showJBContextMenu)

    def _wireUpStorm(self):

        model = TableModelStorm()
        sort = QSortFilterProxyModel()
        sort.setSourceModel(model)
        self.ui.tableViewStorm.setModel(sort)
        self.ui.tableViewStorm.horizontalHeader().setDragEnabled(True)
        self.ui.tableViewStorm.horizontalHeader().setAcceptDrops(True)
        self.ui.tableViewStorm.horizontalHeader().setDragDropMode(QAbstractItemView.DragDrop)
        self.ui.tableViewStorm.horizontalHeader().setDefaultDropAction(Qt.MoveAction)
        self.ui.tableViewStorm.horizontalHeader().setDragDropOverwriteMode(True)
        self.ui.tableViewStorm.horizontalHeader().setDropIndicatorShown(True)

        def showStormContextMenu(pos):
            menu_inx = self.ui.tableViewStorm.model().mapToSource(self.ui.tableViewStorm.indexAt(pos))
            item = self.ui.tableViewStorm.model().sourceModel().model_data[menu_inx.row()]

            target_system_name = item["system_name"]

            lps_ctx_menu = TheraContextMenu(target_system_name)
            lps_ctx_menu.setStyleSheet(Styles.getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewStorm.mapToGlobal(pos))
            if self.handleDestinationActions(
                    act=res, destination={"system_id": Universe.systemIdByName(target_system_name)}):
                return
            elif res == lps_ctx_menu.updateData:
                self.statisticsThread.requestObservationsRecords()
                return
            elif res == lps_ctx_menu.selectRegion:
                self.region_changed_by_system_id.emit(Universe.systemIdByName(target_system_name))
                return

        self.ui.tableViewStorm.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableViewStorm.customContextMenuRequested.connect(showStormContextMenu)

    def _wireUpDatabaseCharacters(self):
        char_model = TableModelPlayers()

        def callOnCharsUpdate():
            char_model.setQuery('select name as Name,'
                                '(CASE active WHEN 0 THEN "No" ELSE "Yes" END) AS Monitor,'
                                '(CASE WHEN key is NULL THEN "" ELSE "ESI" END ) AS Registered,'
                                '(CASE name WHEN (SELECT data FROM cache WHERE key IS "api_char_name")'
                                ' THEN "Yes" ELSE "" END) AS Current FROM players')

        self.tableViewPlayersDelegate = StyledItemDelegatePlayers(self)
        self.tableViewPlayersDelegate.players_edit_changed = self.players_changed
        callOnCharsUpdate()
        sort = QSortFilterProxyModel()
        sort.setSourceModel(char_model)
        self.ui.tableChars.setModel(sort)
        self.ui.tableChars.setItemDelegate(self.tableViewPlayersDelegate)
        self.ui.tableChars.show()
        self.players_changed.connect(callOnCharsUpdate)
        self.region_changed_by_system_id.connect(self.markSystemOnMap)

        def callOnSelChanged(name):
            self.statisticsThread.fetchLocation(fetch=True)
            evegate.setEsiCharName(name)
            # self.rescanIntel()
            self.players_changed.emit()

        self.ui.currentESICharacter.clear()
        self.ui.currentESICharacter.addItems(self.cache.getAPICharNames())
        self.ui.currentESICharacter.setCurrentText(evegate.esiCharName())
        self.ui.currentESICharacter.currentTextChanged.connect(callOnSelChanged)

        def callOnRemoveChar():
            ret = QMessageBox.warning(
                self,
                "Remove Character",
                "Do you really want to remove the ESI registration for the character {}\n\n"
                "The assess key will be removed from database.".format(evegate.esiCharName()),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if ret == QMessageBox.Yes:
                self.cache.removeFromCache("api_char_name")
                self.cache.removeAPIKey(evegate.esiCharName())
                self.ui.currentESICharacter.clear()
                self.ui.currentESICharacter.addItems(self.cache.getAPICharNames())

        self.ui.removeChar.clicked.connect(callOnRemoveChar)

    def updateKillboard(self, system_id):
        ALL_SYSTEMS[system_id].addKill()
        if Globals().follow_kills:
            self.changeRegionBySystemID(system_id)

    def _setupThreads(self):
        logging.info("Set up threads and their connections...")
        self.avatarFindThread = AvatarFindThread()
        self.avatarFindThread.avatar_update.connect(self.updateAvatarOnChatEntry)

        self.filewatcherThread = filewatcher.FileWatcher(self.pathToLogs)
        self.filewatcherThread.file_change.connect(self.logFileChanged)

        self.statisticsThread = MapStatisticsThread()
        self.statisticsThread.statistic_data_update.connect(self.updateStatisticsOnMap)

        self.zkillboard = ZKillMonitor(parent=self)
        self.zkillboard.report_system_kill.connect(self.updateKillboard)
        self.zkillboard.status_kill_mail.connect(lambda online: self.ui.m_qLedZKillboarOnline.setPixmap(
                    QPixmap(u":/Icons/res/online.svg" if online else QPixmap(u":/Icons/res/offline.svg"))))

        #  self.filewatcherThread.addMonitorFile(zkillMonitor.MONITORING_PATH)
        logging.info("Set up threads and their connections done.")

    def _startThreads(self):
        self.avatarFindThread.start()
        self.filewatcherThread.start()
        self.statisticsThread.start()
        self.zkillboard.startConnect()

    def _terminateThreads(self):
        logging.info("Terminating application threads")
        try:
            self.zkillboard.startDisconnect()
            logging.debug("Terminating application threads .")
            SoundManager().quit()
            SoundManager().wait()
            logging.debug("Terminating application threads ..")
            self.avatarFindThread.quit()
            self.avatarFindThread.wait()
            logging.debug("Terminating application threads ...")
            self.filewatcherThread.quit()
            self.filewatcherThread.wait()
            logging.debug("Terminating application threads ....")
            self.statisticsThread.quit()
            self.statisticsThread.wait()
            logging.debug("Terminating application threads .....")
            self.mapTimer.stop()
            if self.apiThread:
                self.apiThread.quit()
                self.apiThread.wait()
            logging.info("Termination of application threads done.")
        except Exception as ex:
            logging.critical(ex)
            pass

    def focusMapOnSystem(self, system):
        """
            Centers the given system on the current map, if the System is not part of the map, noting will be changed.
        Args:
            system: System or system_id of the system to be centered on screen

        Returns:
            None
        """
        if type(system) is System:
            selected_system = system
        elif type(system) is int and system in self.systemsById:
            selected_system = self.systemsById[system]
        else:
            return
        if selected_system in self.systems_on_map.values():
            pt_system = self.ui.mapView.scrollPositionFromMapCoordinate(selected_system.mapCoordinates)
            self.ui.mapView.setScrollPosition(pt_system, animate=True)
            self.ui.mapView.update()

    @Slot()
    def navigateBackward(self):
        """
        Implements the backward forward mouse key functions

        Returns:

        """
        region_name, pos, zoom = self.region_queue.undo()
        if region_name:
            self.changeRegionByName(region_name=region_name, update_queue=False)
            self.ui.mapView.setZoomAndScrollPos(zoom, pos)

    @Slot()
    def navigateForward(self):
        """
        Implements the backward forward mouse key functions
        Returns:

        """
        region_name, pos, zoom = self.region_queue.redo()
        if region_name:
            self.changeRegionByName(region_name=region_name, update_queue=False)
            self.ui.mapView.setZoomAndScrollPos(zoom, pos)

    def changeRegionByName(self, region_name, system_id=None, update_queue=True) -> None:
        """
            Change to a region and highlight a single system.
            The Map will be configured and a rescan of the intel will be performed
        Args:
            region_name: name of the region to be activated
            system_id: id of the system to highlight or None
            update_queue: update the undo/redo queue

        Returns:
            None
        """
        if self.curr_region_name == region_name:
            return
        if update_queue:
            curr_pos = self.ui.mapView.scrollPosition()
            curr_zoom = self.ui.mapView.zoomFactor()
            self.region_queue.enqueue((self.curr_region_name, curr_pos, curr_zoom))

        self.curr_region_name = region_name
        self.dotlan = self.setupRegionMap(region_name)
        self.updateMapView()
        self.updateRegionMap()
        if update_queue:
            if system_id is not None:
                self.focusMapOnSystem(system_id)
            else:
                pt_system = self.ui.mapView.scrollPositionFromMapCoordinate(
                    QRectF(QPointF(0.0, 0.0), self.ui.mapView.imgSize))
                self.ui.mapView.setScrollPosition(pt_system)
                self.ui.mapView.update()
        self.rescanIntel()
        self.region_changed.emit(region_name)

    def changeRegionBySystemID(self, system_id: int) -> None:
        """
            change to the region of the system with the given id, the intel will be rescanned
            and the cache region_name will be updated.
        Args:
            system_id(int): id of the system

        Returns:
            None:
        """
        if type(system_id) is int:
            self.changeRegionByName(region_name=Universe.regionNameFromSystemID(system_id), system_id=system_id)

    @staticmethod
    def loadSVGMapFile(cache, region_name) -> Optional[str]:
        """
            Reads the regions svg content in order res/mapdata folder, filesystem, cache or dotlan
        Args:
            cache:
            region_name:

        Returns:

        """
        res_file_name = os.path.join("vi", "ui", "res", "mapdata",
                                     "{0}.svg".format(evegate.convertRegionNameForDotlan(region_name)))

        if resourcePathExists(res_file_name):
            with open(resourcePath(res_file_name)) as svgFile:
                svg = svgFile.read()
                return svg

        file_name = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "mapdata", "{0}.svg".format(
                evegate.convertRegionNameForDotlan(region_name)))
        if os.path.exists(file_name):
            with open(file_name) as svgFile:
                svg = svgFile.read()
                return svg

        cache_key = "_".join(("mapdata", "svg", evegate.convertRegionNameForDotlan(region_name))).lower()
        svg = cache.getFromCache(cache_key)
        if svg is None or len(svg) < 100:
            try:
                svg = evegate.getSvgFromDotlan(region=region_name, dark=True)
                if svg is None or len(svg) > 100:
                    cache.putIntoCache(cache_key, value=svg, max_age=365*24*60*60)
                    return svg
                else:
                    return None
            except (Exception,) as e:
                logging.error(e)
                return None
        else:
            return svg

    def setupRegionMap(self, region_name):
        """
            Prepares a new dotlan object for the selected region
        Args:
            region_name:

        Returns:

        """
        if not region_name:
            region_name = "Providence"
        svg = self.loadSVGMapFile(self.cache, region_name)
        if svg is None:
            return None

        region_map = dotlan.Map(
            region_name=region_name,
            svg_file=svg,
            set_jump_maps_visible=self.showJumpbridge(),
            set_statistic_visible=self.showStatistic(),
            set_adm_visible=self.showADMOnMap(),
            set_jump_bridges=self.cache.getJumpGates())

        self.setInitialMapPositionForRegion(region_name)
        return region_map

    @Slot()
    def rescanIntel(self) -> None:
        """
            Locks the FileWatcher and rescans all files for the modification time.
            A request for ESI players location will be sent and a Map update will be started.
        Returns:
            Nobe
        """
        try:
            self.clearIntelChat()
            now = datetime.datetime.now()
            for file_path in self.filewatcherThread.files:
                if file_path.endswith(".txt"):
                    path, file = os.path.split(file_path)
                    room_name = ChatParser.roomNameFromFileName(file)
                    modify_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    delta = now - modify_time
                    if (delta.total_seconds() < 60 * Globals().intel_time) and (delta.total_seconds() > 0):
                        if room_name in self.room_names:
                            self.logFileChanged(file_path, rescan=True)
        except Exception as e:
            logging.error(e)

        if hasattr(self, "filewatcherThread"):
            self.filewatcherThread.paused = False

    def _startStatisticTimer(self):
        statistic_timer = QTimer(self)
        statistic_timer.timeout.connect(self.statisticsThread.requestStatistics)
        statistic_timer.timeout.connect(self.pruneOutdatedMessages)
        statistic_timer.start(60*1000)

        eve_scout_timer = QTimer(self)
        eve_scout_timer.timeout.connect(self.statisticsThread.requestWormholes)
        eve_scout_timer.start(20*1000)

    def closeEvent(self, event):
        """
            Persisting things to the cache before closing the window
        """
        # Program state to cache (to read it on next startup)
        settings = ((None, "restoreGeometry", str(self.saveGeometry()), True),
                    (None, "restoreState", str(self.saveState()), True),
                    ("ui.splitter", "restoreGeometry", str(self.ui.splitter.saveGeometry()), True),
                    ("ui.splitter", "restoreState", str(self.ui.splitter.saveState()), True),
                    (None, "changeChatFontSize", ChatEntryWidget.TEXT_SIZE),
                    (None, "changeAlwaysOnTop", self.ui.actionAlwaysOnTop.isChecked()),
                    (None, "changeShowAvatars", self.showAvatar),
                    (None, "changeAlarmDistance", self.alarmDistance),
                    (None, "changeSound", self.ui.actionActivateSound.isChecked()),
                    (None, "changeChatVisibility", self.ui.actionShowTabs.isChecked()),
                    (None, "loadInitialMapPositions", self.mapPositionsDict),
                    (None, "setSoundVolume", SoundManager().soundVolume),
                    (None, "changeFrameless", self.ui.actionFramelessWindow.isChecked()),
                    (None, "changeUseSpokenNotifications", self.ui.actionUseSpokenNotifications.isChecked()),
                    (None, "changeAutoChangeRegion", self.autoChangeRegion),
                    (None, "changeInvertMouseWheel", self.invertWheel),
                    (None, "setShowJumpbridge", self.showJumpbridge()),
                    (None, "setShowADMOnMap", self.showADMOnMap()),
                    (None, "setShowStatistic", self.showStatistic()),
                    (None, "changeTheme", self.cache.getFromCache("theme")),
                    (None, "changeIntelTime", Globals().intel_time),
                    (None, "changeRegionByName", self.curr_region_name))

        self.cache.putIntoCache("version", str(vi.version.VERSION), 60 * 60 * 24 * 30)
        self.cache.putIntoCache("settings", str(settings), 60 * 60 * 24 * 30)
        self._terminateThreads()
        event.accept()
        QtCore.QCoreApplication.quit()

    @Slot(bool)
    def changeChatVisibility(self, value: bool):
        self.ui.actionShowTabs.setChecked(value)

    @Slot(bool)
    def changeAutoChangeRegion(self, value=None):
        if value is None:
            value = self.ui.actionAutoSwitchRegions.isChecked()
        self.ui.actionAutoSwitchRegions.setChecked(value)
        self.autoChangeRegion = value

    @Slot(bool)
    def changeUseSpokenNotifications(self, value=None):
        if SoundManager().platformSupportsSpeech():
            if value is None:
                value = self.ui.actionUseSpokenNotifications.isChecked()
            self.ui.actionUseSpokenNotifications.setChecked(value)
            SoundManager().setUseSpokenNotifications(value)
        else:
            self.ui.actionUseSpokenNotifications.setChecked(False)
            self.ui.actionUseSpokenNotifications.setEnabled(False)

    def changeIntelTime(self, intel_time):
        self._updateIntelActions(intel_time)
        Globals().intel_time = intel_time
        self.ui.timeInfo.setText("All Intel (past {} minutes)".format(Globals().intel_time))
        self.rescanIntel()

    @Slot(object)
    def changeTheme(self, th=None):
        if type(th) is str:
            if th is not None:
                for action in self.themeGroup.actions():
                    if action.theme == th:
                        action.setChecked(True)
        action = self.themeGroup.checkedAction()
        styles = Styles()
        styles.setStyle(action.theme)
        theme = styles.getStyle()
        self.dotlan.updateStyle()
        self.setStyleSheet(theme)
        logging.info("Chane to GUI theme: {}".format(action.theme))
        self.cache.putIntoCache("theme", action.theme, 60 * 60 * 24 * 365)

    def changeSound(self, value=None, disable=False):
        if disable:
            self.ui.actionActivateSound.setChecked(False)
            self.ui.actionActivateSound.setEnabled(False)
            self.ui.actionUseSpokenNotifications(False)
            self.ui.actionSoundSetup.setEnabled(False)
            QMessageBox.warning(
                self, "Sound disabled",
                "The lib 'pyglet' which is used to play sounds cannot be found, ""so the soundsystem is disabled.\n"
                "If you want sound, please install the 'pyglet' library. This warning will not be shown again.",
                QMessageBox.Ok)
        else:
            if value is None:
                value = self.ui.actionActivateSound.isChecked()
            self.ui.actionActivateSound.setChecked(value)
            SoundManager().soundActive = value

    @Slot(bool)
    def changeAlwaysOnTop(self, value=None):
        if value is None:
            value = self.ui.actionAlwaysOnTop.isChecked()
        do_show = self.isVisible()
        if do_show:
            self.hide()
        self.ui.actionAlwaysOnTop.setChecked(value)
        if value:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags((self.windowFlags() & (~Qt.WindowStaysOnTopHint))
                                | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)

        if do_show:
            self.show()

    @Slot(bool)
    def changeFrameless(self, value=None):
        if value is None:
            value = not self.ui.frameButton.isVisible()
        do_show = self.isVisible()
        if do_show:
            self.hide()
        if value:
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
            self.changeAlwaysOnTop(True)
        else:
            self.setWindowFlags(self.windowFlags() & (~Qt.FramelessWindowHint)
                                | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)
        self.ui.menubar.setVisible(not value)
        self.ui.frameButton.setVisible(value)
        self.ui.actionFramelessWindow.setChecked(value)

        if do_show:
            self.show()

    def changeShowAvatars(self, value=None):
        if value is None:
            value = self.ui.actionShowChatAvatars.isChecked()
        self.ui.actionShowChatAvatars.setChecked(value)
        ChatEntryWidget.SHOW_AVATAR = value
        for entry in self.chatEntries:
            entry.ui.avatarLabel.setVisible(value)

    def changeChatFontSize(self, font_size):
        if font_size:
            ChatEntryWidget.TEXT_SIZE = font_size
            for entry in self.chatEntries:
                entry.changeFontSize(font_size)

    @Slot()
    def chatSmaller(self):
        new_size = ChatEntryWidget.TEXT_SIZE - 1
        self.changeChatFontSize(new_size)

    @Slot()
    def chatLarger(self):
        new_size = ChatEntryWidget.TEXT_SIZE + 1
        self.changeChatFontSize(new_size)

    def changeWindowOpacity(self, opacity):
        self._updateWindowOpacityActions(opacity)
        self.setWindowOpacity(opacity)

    def _updateWindowOpacityActions(self, opacity):
        self.ui.actionOpacity_100.setChecked(opacity == 1.0)
        self.ui.actionOpacity_80.setChecked(opacity == 0.8)
        self.ui.actionOpacity_60.setChecked(opacity == 0.6)
        self.ui.actionOpacity_40.setChecked(opacity == 0.4)
        self.ui.actionOpacity_20.setChecked(opacity == 0.2)
        pass

    def _updateIntelActions(self, intel_time):
        self.ui.actionIntel_Time_5_min.setChecked(intel_time == 5)
        self.ui.actionIntel_Time_10_min.setChecked(intel_time == 10)
        self.ui.actionIntel_Time_20_min.setChecked(intel_time == 20)
        self.ui.actionIntel_Time_30_min.setChecked(intel_time == 30)
        self.ui.actionIntel_Time_60_min.setChecked(intel_time == 60)

    def _updateRegionActions(self, system: System):
        if system:
            self.ui.actionOpen_on_dotlan.setText("Show {} on dotlan".format(system.name))
            self.ui.actionOpen_on_dotlan.setEnabled(True)

            self.ui.actionOpen_on_zKillboard.setText("Show {} on zKillboard".format(system.name))
            self.ui.actionOpen_on_zKillboard.setEnabled(True)

            region_name = Universe.regionNameFromSystemID(system.system_id)
            self.ui.actionChange_Region_to.setText("Change region to {}".format(region_name))
            self.ui.actionChange_Region_to.setEnabled(region_name != self.curr_region_name)
        else:
            self.ui.actionOpen_on_dotlan.setEnabled(False)
            self.ui.actionChange_Region_to.setEnabled(False)
            self.ui.actionOpen_on_zKillboard.setEnabled(False)
        self.currentSystem = system

    def _updateAlarmDistanceActions(self, distance):
        """
            Change the alarm distance on actions
        Args:
            distance:

        Returns:

        """
        self.ui.actionAlarm_distance_0.setChecked(distance == 0)
        self.ui.actionAlarm_distance_1.setChecked(distance == 1)
        self.ui.actionAlarm_distance_2.setChecked(distance == 2)
        self.ui.actionAlarm_distance_3.setChecked(distance == 3)
        self.ui.actionAlarm_distance_4.setChecked(distance == 4)
        self.ui.actionAlarm_distance_5.setChecked(distance == 5)

    def changeAlarmDistance(self, distance):
        """
            Change the alarm distance on actions and systems wit and located character
        Args:
            distance:

        Returns:

        """

        for system in ALL_SYSTEMS.values():
            system.changeIntelRange(old_intel_range=self.alarmDistance, new_intel_range=distance)
        self.alarmDistance = distance
        self._updateAlarmDistanceActions(distance)

    def changeJumpbridgesVisibility(self, val):
        self.setShowJumpbridge(val)
        self.dotlan.changeJumpbridgesVisibility(val)

    @Slot(bool)
    def changeADMVisibility(self, val):
        self.setShowADMOnMap(val)
        self.dotlan.changeVulnerableVisibility(val)

    @Slot()
    def changeStatisticsVisibility(self, val):
        self.setShowStatistic(val)
        self.dotlan.changeStatisticsVisibility(val)

    def clipboardChanged(self):
        """ the content of the clip board is used to set jump bridge and poi
        """
        poi_changed = False
        jb_changed = False
        clip_content = self.clipboard.text()
        if clip_content != self.oldClipboardContent:
            for full_line_content in clip_content.splitlines():
                for line_content in tokenize_eve_formatted_text(full_line_content):
                    cb_type, cb_data = evaluateClipboardData(line_content)
                    if cb_type == "poi":
                        if self.cache.putPOI(cb_data):
                            poi_changed = True
                    elif cb_type == "jumpbridge":
                        if self.cache.putJumpGate(
                                src=cb_data["src"],
                                dst=cb_data["dst"],
                                src_id=cb_data["id_src"],
                                dst_id=cb_data["id_dst"],
                                json_src=cb_data["json_src"],
                                json_dst=cb_data["json_dst"]):
                            jb_changed = True
                    elif cb_type == "link":
                        QDesktopServices.openUrl(cb_data)
            self.oldClipboardContent = clip_content
            if poi_changed:
                self.poi_changed.emit()
            if jb_changed:
                self.jbs_changed.emit()

    def mapLinkClicked(self, url: QtCore.QUrl) -> None:
        """
            Opens the solar system dialog
        Args:
            url:

        Returns:
            None
        """
        system_name = str(url.path().split("/")[-1])
        if system_name in self.systems_on_map:
            system = self.systems_on_map[system_name]
            sc = SystemChat(self, SystemChat.SYSTEM, system, self.chatEntries, self.knownPlayerNames)
            self.chat_message_added.connect(sc.addChatEntry)
            self.avatar_loaded.connect(sc.newAvatarAvailable)
            sc.location_set.connect(self.setLocation)
            sc.repaint_needed.connect(self.updateMapView)
            sc.show()

    def markSystemOnMap(self, system_marked) -> None:
        """
            Marks the selected system, if needed a region change will be initialized as needed.
        Args:
            system_marked: name or id of the system

        Returns:
            None:

        """
        if type(system_marked) is str:
            system = ALL_SYSTEMS[Universe.systemIdByName(system_marked)]
        elif type(system_marked) is int:
            system = ALL_SYSTEMS[system_marked]
        elif type(system_marked) is System:
            system = system_marked
        else:
            system = None
        if system:
            system.mark()
            if system in self.systems_on_map.values():
                self.focusMapOnSystem(system.system_id)
            else:
                self.changeRegionBySystemID(system.system_id)
                self.focusMapOnSystem(system.system_id)

    @staticmethod
    def updateCharLocationOnMap(system_id: int, char_name: str, alarm_distance: int) -> None:
        """
            Remove the char on the systems, then assign to the system with id system_is and distance
        Args:
            system_id:
            char_name:
            alarm_distance:

        Returns:

        """
        for system in ALL_SYSTEMS.values():
            system.removeLocatedCharacter(char_name, alarm_distance)

        if system_id in ALL_SYSTEMS.keys():
            system = ALL_SYSTEMS[system_id]
            system.addLocatedCharacter(char_name, alarm_distance)
            logging.info("The current location of the character '{}' changed to the system '{}'".format(
                char_name, system.name))

    @Slot()
    def locateChar(self):
        self.statisticsThread.fetchLocation(fetch=True)
        self.statisticsThread.requestLocations()

    def setLocation(self, char_name, system_in, change_region: bool = False) -> None:
        """
        Change the location of the char to the given system, if requested the region may be changed.
        The selected system will be center of the screen.

        Args:
            char_name: name of the character
            system_in: system name
            change_region: allow change of the region

        Returns:
            None:
        """
        system_id = system_in if type(system_in) is int else Universe.systemIdByName(system_in)
        system_name = system_in if type(system_in) is str else Universe.systemNameById(system_in)

        self.updateCharLocationOnMap(system_id, char_name, self.alarmDistance)

        if system_name in self.systems_on_map:
            if change_region:
                self.focusMapOnSystem(system_id)
        else:
            if change_region:
                try:
                    selected_region_name = Universe.regionNameFromSystemID(system_id)
                    if selected_region_name != self.curr_region_name:
                        self.changeRegionByName(region_name=selected_region_name, system_id=system_id)
                except (Exception,) as e:
                    logging.error(e)
                    pass

    def updateRegionMap(self):
        # self.ui.regionView.setContent(self.dotlan)
        pass

    def updateMapView(self):
        try:
            if self.dotlan and self.dotlan.is_dirty():
                self.mapTimer.stop()
                self.ui.mapView.setContent(self.dotlan)
                self.mapTimer.start(MAP_UPDATE_INTERVAL_MSEC)
            else:
                pass
        except Exception as e:
            logging.error("Error updateMapView failed: {0}".format(str(e)))
            pass

    def loadInitialMapPositions(self, new_dictionary):
        self.mapPositionsDict = new_dictionary

    def setInitialMapPositionForRegion(self, region_name):
        try:
            if not region_name:
                self.curr_region_name = self.cache.getFromCache("region_name")
            if region_name and region_name in self.mapPositionsDict:
                xy = self.mapPositionsDict[region_name]
                self.initialMapPosition = QPointF(xy[0], xy[1])
            else:
                self.initialMapPosition = None
        except Exception as e:
            logging.error("Error setInitialMapPositionForRegion failed: {0}".format(str(e)))
            pass

    @Slot()
    def fixupScrollBars(self):
        fac = self.ui.mapView.zoomFactor()
        pos = self.ui.mapView.scrollPosition()
        size = self.ui.mapView.imgSize
        self.ui.mapHorzScrollBar.setPageStep(size.width())
        self.ui.mapVertScrollBar.setPageStep(size.height())
        self.ui.mapHorzScrollBar.setRange(int(min(pos.x(), 0)), int(size.width()*fac))
        self.ui.mapVertScrollBar.setRange(int(min(pos.y(), 0)), int(size.height()*fac))
        self.ui.mapHorzScrollBar.setValue(int(pos.x()))
        self.ui.mapVertScrollBar.setValue(int(pos.y()))
        self.ui.mapView.update()

    def showChatroomChooser(self):
        chooser = ChatroomChooser(self)
        chooser.rooms_changed.connect(self.changedRoomNames)
        chooser.show()

    def callOnJbUpdate(self):
        return

    @Slot()
    def showJumpbridgeChooser(self):
        url = self.cache.getFromCache("jumpbridge_url")
        chooser = JumpbridgeChooser(self, url)
        chooser.set_jumpbridge_url.connect(self.updateJumpbridgesFromFile)
        chooser.update_jumpbridge.connect(self.callOnJbUpdate)
        chooser.delete_jumpbridge.connect(self.callDeleteJumpbridge)
        chooser.show()

    @staticmethod
    def setSoundVolume(value):
        SoundManager().setSoundVolume(value)

    def callDeleteJumpbridge(self):
        self.cache.clearJumpGate(None)
        self.jbs_changed.emit()

    def updateJumpbridgesFromFile(self, url):
        """ Updates the jumpbridge cache from url or local a local file, following
            the file format as described:

            src » dst [id_src id_dst json_src_struct json_dst_struct]

        Args:
            url: url or path

        Returns:

        """
        if url is None:
            url = ""
        try:
            data = []
            if url != "":
                if url.startswith("http://") or url.startswith("https://"):
                    resp = requests.get(url)
                    for line in resp.iter_lines(decode_unicode=True):
                        parts = line.strip().split()
                        if len(parts) > 2:
                            data.append(parts)
                elif os.path.exists(url):
                    with open(url, 'r') as f:
                        content = f.readlines()

                self.cache.clearJumpGate(None)
                self.jbs_changed.emit()

                for line in content:
                    jump_bridge_text = parse.parse("{src} » {dst}", line)
                    if jump_bridge_text:
                        self.cache.putJumpGate(src=jump_bridge_text.named["src"], dst=jump_bridge_text.named["dst"])
                        continue
                    jump_bridge_text = parse.parse("{src} » {dst} {}", line)
                    if jump_bridge_text:
                        self.cache.putJumpGate(src=jump_bridge_text.named["src"], dst=jump_bridge_text.named["dst"])
                        continue
                    jump_bridge_text = parse.parse("{id} {src} --> {dst}", line)
                    if jump_bridge_text:
                        self.cache.putJumpGate(src=jump_bridge_text.named["src"], dst=jump_bridge_text.named["dst"])
                        continue
                    jump_bridge_text = parse.parse("{src} <-> {dst}", line)
                    if jump_bridge_text:
                        self.cache.putJumpGate(src=jump_bridge_text.named["src"], dst=jump_bridge_text.named["dst"])
                        continue
                    jump_bridge_text = parse.parse("{src} --> {dst}", line)
                    if jump_bridge_text:
                        self.cache.putJumpGate(src=jump_bridge_text.named["src"], dst=jump_bridge_text.named["dst"])
                        continue

                self.jbs_changed.emit()

            self.cache.putIntoCache("jumpbridge_url", url)

        except Exception as e:
            logging.error("Error setJumpbridges failed: {0}".format(str(e)))
            QMessageBox.warning(self, "Loading jumpbridges failed!", "Error: {0}".format(str(e)), QMessageBox.Ok)

    def handleRegionMenuItemSelected(self, action=None):
        self.ui.actionCatchRegion.setChecked(False)
        self.ui.actionProvidenceRegion.setChecked(False)
        self.ui.actionQueriousRegion.setChecked(False)
        self.ui.actionWickedcreekScaldingpassRegion.setChecked(False)
        self.ui.actionProvidenceCatchRegion.setChecked(False)
        self.ui.actionProvidenceCatchCompactRegion.setChecked(False)
        if action:
            action.setChecked(True)
            selected_region_name = str(action.property("regionName"))
            self.changeRegionByName(region_name=selected_region_name)

    @staticmethod
    def formatZKillMessage(message):
        soup = dotlan.BeautifulSoup(message, "lxml-xml")
        [s.extract() for s in soup(['href', 'br'])]
        res = soup.getText()
        http_start = res.find("http")
        if http_start != -1:
            http_end = res.find(" ", http_start)
            substr = res[http_start:http_end]
            res = res.replace(substr, "")
        corp_start = res.find("<")
        if corp_start != -1:
            corp_end = res.find(" ", corp_start)
            substr = res[corp_start:corp_end]
            res = res.replace(substr, "")
        res = res.replace("(", "from ")
        res = res.replace(")", ", ")
        return res

    def addMessageToDatabase(self, message: Message):
        if message and message.user:
            if message.roomName != CTX.ZKILLBOARD_ROOM_NAME:
                data = evegate.esiCharactersPublicInfo(message.user)
                if data:
                    self.cache.putJsonToAvatar(
                        player_name=message.user,
                        json_txt=json.dumps(data),
                        alliance_id=data["alliance_id"] if "alliance_id" in data.keys() else None,
                        max_age=3600
                    )

    def addMessageToIntelChat(self, message: Message):
        scroll_to_bottom = False
        if self.ui.chatListWidget.verticalScrollBar().value() == self.ui.chatListWidget.verticalScrollBar().maximum():
            scroll_to_bottom = True

        if self.ui.actionUseSpokenNotifications.isChecked():
            if message.roomName == CTX.ZKILLBOARD_ROOM_NAME:
                message_text = self.formatZKillMessage(message.plainText)
            else:
                message_text = message.plainText
            SoundManager().playSound(
                name="alarm_1",
                abbreviated_message="Massage from {user},  {msg}, The status is now {stat}".format(
                    user=message.user, msg=message_text, stat=message.status))

        chat_entry_widget = ChatEntryWidget(message)
        avatar_icon = None
        if message.user == "SPYGLASS":
            with open(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")), "rb") as f:
                avatar_icon = f.read()
        elif message.user == "zKillboard.com":
            chat_entry_widget.updateAvatar(":/icons/zKillboard.svg")
        elif message.user != "zKillboard.com":
            avatar_icon = self.cache.getImageFromAvatar(message.user)
            if avatar_icon is None and self.showAvatar:
                self.avatarFindThread.addChatEntry(chat_entry_widget)
        if avatar_icon:
            chat_entry_widget.updateAvatar(avatar_icon)

        list_widget_item = ChatEntryItem(
            key=message.timestamp.strftime("%Y%m%d %H%M%S"),
            listview=self.ui.chatListWidget)
        list_widget_item.setSizeHint(chat_entry_widget.sizeHint())
        self.ui.chatListWidget.addItem(list_widget_item)
        self.ui.chatListWidget.setItemWidget(list_widget_item, chat_entry_widget)

        self.chatEntries.append(chat_entry_widget)
        chat_entry_widget.mark_system.connect(self.markSystemOnMap)
        self.chat_message_added.emit(chat_entry_widget, message.timestamp)
        if scroll_to_bottom:
            self.ui.chatListWidget.scrollToBottom()

    @Slot()
    def clearIntelChat(self):
        try:
            for system in ALL_SYSTEMS.values():
                system.clearIntel()
        except Exception as e:
            logging.error(e)
        self.chatparser.clearIntel()
        try:
            while self.ui.chatListWidget.count() > 0:
                item = self.ui.chatListWidget.item(0)
                entry = self.ui.chatListWidget.itemWidget(item)
                self.chatEntries.remove(entry)
                self.ui.chatListWidget.takeItem(0)
        except Exception as e:
            logging.error(e)

    def pruneOutdatedMessages(self):
        """
            prune all outdated messages
        Returns:

        """
        try:
            expired = time.mktime(currentEveTime().timetuple()) - (60 * Globals().intel_time)
            self.chatparser.pruneMessages(expired)
            for row in range(self.ui.chatListWidget.count()):
                chat_list_widget_item = self.ui.chatListWidget.item(0)
                chat_entry_widget = self.ui.chatListWidget.itemWidget(chat_list_widget_item)
                message = chat_entry_widget.message
                if expired > time.mktime(message.timestamp.timetuple()):
                    self.chatEntries.remove(chat_entry_widget)
                    self.ui.chatListWidget.takeItem(0)
                    try:
                        for _, system in enumerate(message.affectedSystems):
                            system.pruneMessage(message)
                    except Exception as e:
                        logging.error(e)
        except Exception as e:
            logging.error(e)

    def changedRoomNames(self, names):
        self.cache.putIntoCache("room_names", u",".join(names), 60 * 60 * 24 * 365 * 5)
        self.chatparser.rooms = names

    @Slot()
    def showInfo(self):
        info_dialog = QtWidgets.QDialog(self)
        info_dialog.ui = Ui_EVESpyInfo()
        info_dialog.ui.setupUi(info_dialog)
        version_text = info_dialog.ui.versionLable.text().replace("#ver#", vi.version.VERSION)
        info_dialog.ui.versionLable.setText(version_text)
        info_dialog.show()

    def selectSoundFile(self, mask, dialog):
        filename = QFileDialog.getOpenFileName(self, caption="Select sound file")
        if len(filename):
            SoundManager().setSoundFile(mask, filename[0])
        else:
            SoundManager().setSoundFile(mask, "")
        if dialog:
            dialog.ui.soundAlarm_1.setText(SoundManager().soundFile("alarm_1"))
            dialog.ui.soundAlarm_2.setText(SoundManager().soundFile("alarm_2"))
            dialog.ui.soundAlarm_3.setText(SoundManager().soundFile("alarm_3"))
            dialog.ui.soundAlarm_4.setText(SoundManager().soundFile("alarm_4"))
            dialog.ui.soundAlarm_5.setText(SoundManager().soundFile("alarm_5"))

    @Slot()
    def showSoundSetup(self):
        dialog = QtWidgets.QDialog(self)
        dialog.ui = Ui_SoundSetup()
        dialog.ui.setupUi(dialog)
        dialog.ui.volumeSlider.setValue(int(SoundManager().soundVolume))
        dialog.ui.volumeSlider.valueChanged[int].connect(SoundManager().setSoundVolume)
        dialog.ui.testSoundButton.clicked.connect(
            lambda: SoundManager().playSound(name="alarm", abbreviated_message="Testing the playback sound system."))
        dialog.ui.palyAlarm_1.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_1", abbreviated_message="Alarm distance 1."))
        dialog.ui.palyAlarm_2.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_2", abbreviated_message="Alarm distance 2."))
        dialog.ui.palyAlarm_3.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_3", abbreviated_message="Alarm distance 3."))
        dialog.ui.palyAlarm_4.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_4", abbreviated_message="Alarm distance 4."))
        dialog.ui.palyAlarm_5.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_5", abbreviated_message="Alarm distance 5."))
        dialog.ui.selectAlarm_1.clicked.connect(lambda: self.selectSoundFile("alarm_1", dialog))
        dialog.ui.selectAlarm_2.clicked.connect(lambda: self.selectSoundFile("alarm_2", dialog))
        dialog.ui.selectAlarm_3.clicked.connect(lambda: self.selectSoundFile("alarm_3", dialog))
        dialog.ui.selectAlarm_4.clicked.connect(lambda: self.selectSoundFile("alarm_4", dialog))
        dialog.ui.selectAlarm_5.clicked.connect(lambda: self.selectSoundFile("alarm_5", dialog))
        dialog.ui.soundAlarm_1.setText(SoundManager().soundFile("alarm_1"))
        dialog.ui.soundAlarm_2.setText(SoundManager().soundFile("alarm_2"))
        dialog.ui.soundAlarm_3.setText(SoundManager().soundFile("alarm_3"))
        dialog.ui.soundAlarm_4.setText(SoundManager().soundFile("alarm_4"))
        dialog.ui.soundAlarm_5.setText(SoundManager().soundFile("alarm_5"))
        dialog.ui.useSoundSystem.setDefaultAction(self.ui.actionActivateSound)
        dialog.ui.useSpokenNotifications.setDefaultAction(self.ui.actionUseSpokenNotifications)

        def defaultSoundSetup():
            self.changeUseSpokenNotifications(False)
            SoundManager().setSoundFile("alarm_1", "")
            SoundManager().setSoundFile("alarm_2", "")
            SoundManager().setSoundFile("alarm_3", "")
            SoundManager().setSoundFile("alarm_4", "")
            SoundManager().setSoundFile("alarm_5", "")
            SoundManager().setSoundVolume(50)
            dialog.ui.volumeSlider.setValue(int(SoundManager().soundVolume))
            dialog.ui.soundAlarm_1.setText(SoundManager().soundFile("alarm_1"))
            dialog.ui.soundAlarm_2.setText(SoundManager().soundFile("alarm_2"))
            dialog.ui.soundAlarm_3.setText(SoundManager().soundFile("alarm_3"))
            dialog.ui.soundAlarm_4.setText(SoundManager().soundFile("alarm_4"))
            dialog.ui.soundAlarm_5.setText(SoundManager().soundFile("alarm_5"))
            self.ui.actionActivateSound.setChecked(True)
            self.ui.actionUseSpokenNotifications.setChecked(False)

            SoundManager().loadSoundFiles()

        dialog.ui.defaultSounds.clicked.connect(defaultSoundSetup)
        dialog.ui.applySoundSetting.clicked.connect(dialog.accept)
        dialog.show()

    def systemTrayActivated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            if self.isMinimized():
                self.showNormal()
                self.activateWindow()
            elif not self.isActiveWindow():
                self.activateWindow()
            else:
                self.showMinimized()

    def updateAvatarOnChatEntry(self, entry, data):
        """
        Assigns the blob data as pixmap to the entry, if a pixmap could be loaded directly, otherwise
        the blob will be loaded wia avatar thread
        Args:
            entry: new message
            data: blob of image

        Returns:
            None: emits avatar_loaded
        """
        if entry.updateAvatar(data):
            # update all pending message for the user
            self.avatar_loaded.emit(entry.message.user, data)
        else:
            # retry to fetch avatar, but clear database
            self.avatarFindThread.addChatEntry(entry, clear_cache=True)

    def updateStatisticsOnMap(self, data):

        if STAT.STATISTICS in data.keys():
            self.mapStatisticCache = data[STAT.STATISTICS]
            if self.dotlan:
                self.dotlan.addSystemStatistics(self.mapStatisticCache)
        if STAT.SERVER_STATUS in data.keys():
            server_status = data[STAT.SERVER_STATUS]
            if server_status["players"] > 0:
                self.ui.m_qLedOnline.setPixmap(QPixmap(u":/Icons/res/online.svg"))
            else:
                self.ui.m_qLedOnline.setPixmap(QPixmap(u":/Icons/res/offline.svg"))
            self.ui.m_qPlayerOnline.setText("Players ({players}) Server version ({server_version})".format(
                **server_status))

        if STAT.THERA_WORMHOLES_VERSION in data.keys():
            thera_wormhole_version = data[STAT.THERA_WORMHOLES_VERSION]
            self.ui.m_qEveScoutVersion.setText(thera_wormhole_version["api_version"])

        if STAT.OBSERVATIONS_RECORDS in data.keys():
            observations_records = data[STAT.OBSERVATIONS_RECORDS]
            self.ui.tableViewStorm.model().sourceModel().updateObservationsRecords(observations_records)

        if STAT.THERA_WORMHOLES in data.keys():
            thera_wormhole = data[STAT.THERA_WORMHOLES]
            if thera_wormhole and len(thera_wormhole) > 0:
                self.ui.m_qLedEveScout.setPixmap(QPixmap(u":/Icons/res/online.svg"))
            else:
                self.ui.m_qLedEveScout.setPixmap(QPixmap(u":/Icons/res/offline.svg"))
            self.setTheraConnections(thera_wormhole)
            logging.debug("Thera wormholes successfully fetched.")

        if STAT.SOVEREIGNTY in data:
            if self.dotlan:
                self.dotlan.setSystemSovereignty(data[STAT.SOVEREIGNTY])

        if STAT.STRUCTURES in data:
            if self.dotlan:
                self.dotlan.setSystemStructures(data[STAT.STRUCTURES])

        if STAT.INCURSIONS in data:
            if self.dotlan:
                self.dotlan.setIncursionSystems(data[STAT.INCURSIONS])

        if STAT.CAMPAIGNS in data:
            if self.dotlan:
                self.dotlan.setCampaignsSystems(data[STAT.CAMPAIGNS])

        if STAT.REGISTERED_CHARS in data:
            char_data = data[STAT.REGISTERED_CHARS]
            char_data_online = []
            for itm in char_data:
                is_esi_char = evegate.esiCharName() == itm["name"]
                if not itm["online"] and not is_esi_char:
                    self.setLocation(itm["name"], itm["system"]["name"], change_region=False)
                else:
                    char_data_online.append(itm)

            for itm in char_data_online:
                self.setLocation(itm["name"], itm["system"]["name"], change_region=True)
                self.focusMapOnSystem(itm["system"]["system_id"])

        if STAT.CHECK_FOR_UPDATE in data:
            self.checkForUpdate(data[STAT.CHECK_FOR_UPDATE])

    @Slot()
    def clearCacheFile(self):
        ret = QMessageBox.warning(
            self,
            "Clear Database",
            "Do you really want to clear the Database.\n\n"
            "All icons an character public data, alliance and map data will be removed.\n"
            "Your characters ESI assess keys will not be removed from database.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if ret == QMessageBox.Yes:
            self.cache.removeFromCache("api_char_name")
            self.cache.clearDataBase()

    @Slot()
    def zoomMapIn(self):
        self.ui.mapView.zoomIn()

    @Slot()
    def zoomMapOut(self):
        self.ui.mapView.zoomOut()

    def logFileChanged(self, path, rescan=False):
        locale_to_set = dict()
        messages = self.chatparser.fileModified(path, self.systems_on_map, rescan)
        for message in messages:
            if message.status == States.LOCATION:
                locale_to_set[message.user] = message.affectedSystems
                self.statisticsThread.fetchLocation(fetch=True)
            elif message.canProcess():
                self.addMessageToIntelChat(message)
                self.addMessageToDatabase(message)

        for name, systems in locale_to_set.items():
            self._updateKnownPlayerAndMenu(name)
            for sys_name in systems:
                self.setLocation(name, sys_name, self.autoChangeRegion)

    def systemUnderMouse(self, pos: QPoint) -> Optional[dotlan.System]:
        """returns the name of the system under the mouse pointer
        """
        for system in self.systems_on_map.values():
            if system.mapCoordinates.contains(pos):
                return system
        return None

    def showMapContextMenu(self, pos):
        """ checks if there is a system below the mouse position, if the systems region differs from the current
            region, the menu item to change the current region is added.
        """
        selected_system = self.systemUnderMouse(self.ui.mapView.mapPosFromPoint(pos))
        map_ctx_menu = MapContextMenu(self.ui)
        map_ctx_menu.setStyleSheet(Styles.getStyle())
        if selected_system:
            self._updateRegionActions(selected_system)
        else:
            self._updateRegionActions(None)
        res = map_ctx_menu.exec_(self.ui.mapView.mapToGlobal(pos))
        if selected_system:
            if self.handleDestinationActions(res, destination={"system_id": selected_system.system_id}):
                return
            elif res == map_ctx_menu.clearJumpGate:
                self.cache.clearJumpGate(selected_system.name)
                self.jbs_changed.emit()
                return
