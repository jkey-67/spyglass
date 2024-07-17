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
import os
import datetime
import time
import requests
import parse

from typing import Union
from typing import Optional

import logging
from PySide6.QtGui import Qt
from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtCore import QPoint, QPointF, QSortFilterProxyModel, QTimer, Qt, QIODevice
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtGui import QIcon, QImage, QPixmap, QDesktopServices
from PySide6.QtWidgets import (QMessageBox, QStyleOption, QStyle, QFileDialog,
                               QStyledItemDelegate, QApplication, QAbstractItemView)

import vi.version
from vi.universe import Universe
from vi.system import System
from vi import evegate
from vi import dotlan, filewatcher
from vi.states import States
from vi.globals import Globals
from vi.ui import JumpbridgeChooser, ChatroomChooser, RegionChooser, SystemChat, ChatEntryWidget, ChatEntryItem

from vi.cache.cache import Cache, currentEveTime
from vi.resources import resourcePath, resourcePathExists
from vi.soundmanager import SoundManager
from vi.threads import AvatarFindThread, MapStatisticsThread
from vi.redoundoqueue import RedoUndoQueue
from vi.ui.systemtray import TrayContextMenu
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

from vi.universe.routeplanner import RoutPlanner

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtSql import QSqlQueryModel

from vi.ui import Ui_MainWindow, Ui_EVESpyInfo, Ui_SoundSetup

from vi.chatparser.message import Message

from vi.zkillboard import Zkillmonitor

from vi.system import ALL_SYSTEMS

"""
 Timer intervals
"""
MAP_UPDATE_INTERVAL_MSEC = 20
CLIPBOARD_CHECK_INTERVAL_MSEC = 125


class POITableModell(QSqlQueryModel):
    def __init__(self, parent=None):
        super(POITableModell, self).__init__(parent)
        self.cache = Cache()

    def flags(self, index) -> Qt.ItemFlags:
        default_flags = super(POITableModell, self).flags(index)
        if index.isValid():
            if index.column() == 1:
                return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable | default_flags
            else:
                return Qt.ItemIsSelectable | Qt.ItemIsEnabled | default_flags
        else:
            return Qt.ItemIsDropEnabled | default_flags

    def supportedDropActions(self):
        return Qt.MoveAction | Qt.CopyAction

    def dropMimeData(self, data: QtCore.QMimeData, action: Qt.DropAction, row: int, column: int, parent) -> bool:
        if action == Qt.IgnoreAction:
            return True
        if not data.hasFormat('text/plain'):
            return False
        if column > 0:
            return False

        num_rows = self.rowCount(QtCore.QModelIndex())

        if row != -1:
            begin_row = row
        elif parent.isValid():
            begin_row = parent.row()
        else:
            begin_row = num_rows

        if begin_row != num_rows and begin_row != 0:
            begin_row += 1

        encoded_data = data.data('text/plain')

        stream = QtCore.QDataStream(encoded_data, QIODevice.ReadOnly)
        new_items = []
        rows = 0
        while not stream.atEnd():
            text = str()
            stream >> text
            new_items.append(text)
            rows += 1

        # insert the new rows for the dropped items and set the data to these items appropriately
        self.insertRows(begin_row, rows, QtCore.QModelIndex())
        for text in new_items:
            idx = self.index(begin_row, 0, QtCore.QModelIndex())
            self.setData(idx, text, 0)
            self.dataChanged.emit(idx, idx)
            begin_row += 1

        return True

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, indexes):
        mime_data = QtCore.QMimeData()
        # encoded_data = QtCore.QByteArray()
        # stream = QtCore.QDataStream(encoded_data, QIODevice.WriteOnly)
        for index in indexes:
            if index.isValid():
                db_data = self.cache.getPOIAtIndex(index.row())
                text = "<url=showinfo{}//{}>{}</url>".format(
                    db_data["type_id"], db_data["structure_id"], db_data["name"])
                mime_data.setText(text)
        return mime_data

    def keyPressEvent(self, e):
        pass
        # if e == Qt.QKeySequence.Copy:
        #    index = self.currentIndex()


class StyledItemDelegatePOI(QStyledItemDelegate):
    poi_edit_changed = pyqtSignal()

    def __init__(self, parent=None):
        super(StyledItemDelegatePOI, self).__init__(parent)
        self.cache = Cache()

    def paint(self, painter, option, index):
        painter.save()
        if index.column() == 0:
            type_id = index.data()
            type_data = evegate.getTypesIcon(type_id)
            img = QImage.fromData(type_data)
            painter.setClipRect(option.rect)
            painter.drawImage(option.rect.topLeft(), img)
        else:
            super(StyledItemDelegatePOI, self).paint(painter, option, index)
        painter.restore()

    def sizeHint(self, option, index):
        if index.column() == 0:
            return QtCore.QSize(64, 64)
        else:
            return super(StyledItemDelegatePOI, self).sizeHint(option, index)

    def createEditor(self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem,
                     index: Union[
                         QtCore.QModelIndex, QtCore.QPersistentModelIndex]) -> QtWidgets.QWidget:
        if index.column() == 1:
            return QtWidgets.QTextEdit(parent)
        else:
            return super(StyledItemDelegatePOI, self).createEditor(parent, option, index)

    def setEditorData(self, editor, index) -> None:
        if index.column() == 1:
            editor.setText(index.data())
        else:
            super(StyledItemDelegatePOI, self).setEditorData(editor, index)

    def setModelData(self, editor, model, index) -> None:
        src_index = model.mapToSource(index)
        data = self.cache.getPOIAtIndex(src_index.row())
        if data and editor.toPlainText() != index.data():
            self.cache.setPOIItemInfoText(data["destination_id"], editor.toPlainText())
            super(StyledItemDelegatePOI, self).setModelData(editor, model, index)
            self.poi_edit_changed.emit()
        else:
            super(StyledItemDelegatePOI, self).setModelData(editor, model, index)


class MainWindow(QtWidgets.QMainWindow):

    chat_message_added = pyqtSignal(object, object)
    avatar_loaded = pyqtSignal(object, object)
    jbs_changed = pyqtSignal()
    players_changed = pyqtSignal()
    poi_changed = pyqtSignal()
    region_changed_by_system_id = pyqtSignal(int)
    region_changed = pyqtSignal(str)
    current_system_changed = pyqtSignal(str)

    def __init__(self, pat_to_logfile, tray_icon, update_splash=None):

        def update_splash_window_info(string):
            if update_splash:
                update_splash(string)

        update_splash_window_info("Init GUI application")

        QtWidgets.QMainWindow.__init__(self)
        self.cache = Cache()
        self.dotlan_maps = dict()
        self.dotlan = None
        self.region_queue = RedoUndoQueue()
        region_name = self.cache.getFromCache("region_name")
        self.blockSignals(True)
        self.region_stack = list()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        icon = QIcon()
        icon.addPixmap(QtGui.QPixmap(resourcePath(os.path.join("vi", "ui", "res", "eve-sso-login-black-small.png"))),
                       QIcon.Normal, QIcon.Off)

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
        self.ui.connectToEveOnline.setIcon(icon)
        self.ui.connectToEveOnline.setIconSize(QtCore.QSize(163, 38))
        self.ui.connectToEveOnline.setFlat(False)
        self.setWindowTitle(
            "EVE-Spy " + vi.version.VERSION + "{dev}".format(dev="-SNAPSHOT" if vi.version.SNAPSHOT else ""))
        self.taskbarIconQuiescent = QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")))
        self.taskbarIconWorking = QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small_green.png")))
        self.setWindowIcon(self.taskbarIconQuiescent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.pathToLogs = pat_to_logfile
        self.currContent = None
        self.mapTimer = QTimer(self)
        self.mapTimer.timeout.connect(self.updateMapView)
        self.oldClipboardContent = ""
        self.trayIcon = tray_icon
        self.trayIcon.activated.connect(self.systemTrayActivated)
        self.clipboard = QApplication.clipboard()
        self.alarmDistance = 0
        self.lastStatisticsUpdate = 0
        self.chatEntries = []
        self.ui.frameButton.setVisible(False)
        self.initialMapPosition = None
        self.autoChangeRegion = False
        self.mapPositionsDict = {}

        try:
            status = evegate.esiStatus()
            info = "Server ({server_version}) online {players} players started {start_time}.".format(**status)
            logging.info(info)
            update_splash_window_info(info)
        except (Exception,) as e:
            update_splash_window_info("There was no response from the server, perhaps the server is down.")

        update_splash_window_info("Fetch universe system jumps via ESI.")

        self.mapStatisticCache = evegate.esiUniverseSystem_jumps(use_outdated=True)
        update_splash_window_info("Fetch player sovereignty via ESI.")
        self.mapSovereignty = evegate.getPlayerSovereignty(use_outdated=True, fore_refresh=False, show_npc=True)
        update_splash_window_info("Fetch incursions via ESI...")
        self.mapIncursions = evegate.esiIncursions(use_outdated=True)
        update_splash_window_info("Fetch sovereignty campaigns via ESI...")
        self.mapCampaigns = evegate.esiSovereigntyCampaigns(use_outdated=True)
        self.mapJumpGates = self.cache.getJumpGates()
        self.setupMap()
        self.invertWheel = False
        self._connectActionPack()

        update_splash_window_info("Preset application")

        update_splash_window_info("Set up Theme menu - fill in list of themes and add connections")
        self.themeGroup = QActionGroup(self.ui.menu)
        styles = Styles()
        for theme in styles.getStyles():
            action = QAction(theme, None)
            action.setCheckable(True)
            action.theme = theme
            if action.theme == "default":
                action.setChecked(True)
            logging.info("Adding theme {}".format(theme))
            action.triggered.connect(self.changeTheme)
            self.themeGroup.addAction(action)
            self.ui.menuTheme.addAction(action)

        # Load user's toon names
        for api_char_names in self.cache.getAPICharNames():
            if evegate.esiCharactersOnline(api_char_names):
                self._updateKnownPlayerAndMenu(api_char_names)

        if len(self.knownPlayerNames) == 0:
            info_text = "Spyglass scans EVE system logs and remembers your characters as they change systems.\n\n" \
                        "Some features (clipboard KOS checking, alarms, etc.) may not work until your character(s)" "" \
                        "have been registered. Change systems, with each character you want to monitor, while " \
                        "Spyglass is running to remedy this."
            QMessageBox.warning(self, "Known Characters not Found", info_text)

        update_splash_window_info("Update player names")
        # Set up Theme menu - fill in list of themes and add connections

        if self.invertWheel is None:
            self.invertWheel = False
        self.ui.actionInvertMouseWheel.triggered.connect(self.wheelDirChanged)
        self.ui.actionInvertMouseWheel.setChecked(self.invertWheel)
        self._addPlayerMenu()
        self.players_changed.connect(self._addPlayerMenu)

        # Set up user's intel rooms
        update_splash_window_info("Set up user's intel rooms")

        cached_room_name = self.cache.getFromCache("room_names")
        if cached_room_name:
            cached_room_name = cached_room_name.split(",")
        else:
            cached_room_name = ChatroomChooser.DEFAULT_ROOM_MANES
            self.cache.putIntoCache("room_names", u",".join(cached_room_name), 60 * 60 * 24 * 365 * 5)
        self.room_names = cached_room_name

        # Disable the sound UI if sound is not available
        update_splash_window_info("Doublecheck the sound UI if sound is not available...")
        if not SoundManager.soundAvailable:
            self.changeSound(disable=True)
            update_splash_window_info("Sound disabled.")
        else:
            self.changeSound()
            update_splash_window_info("Sound successfully enabled.")

        # Set up Transparency menu - fill in opacity values and make connections
        update_splash_window_info("Set up Transparency menu - fill in opacity values and make connections")
        self.opacityGroup = QActionGroup(self.ui.menu)
        for i in (100, 80, 60, 40, 20):
            action = QAction("Opacity {0}%".format(i), None)
            action.setCheckable(True)
            action.setChecked(i == 100)
            action.opacity = float(i) / 100.0
            action.triggered.connect(self.changeOpacity)
            self.opacityGroup.addAction(action)
            self.ui.menuTransparency.addAction(action)
        self.intelTimeGroup = QActionGroup(self.ui.menu)
        globals_setting = Globals()
        for i in (5, 10, 20, 30, 60):
            action = QAction("Past {0}min".format(i), None)
            action.setCheckable(True)
            action.setChecked(i == globals_setting.intel_time)
            action.intelTime = i
            action.triggered.connect(self.changeIntelTime)
            self.intelTimeGroup.addAction(action)
            self.ui.menuTime.addAction(action)

        self.ui.actionAuto_switch.triggered.connect(self.changeAutoRegion)

        update_splash_window_info("Update chat parser")

        self.chatparser = ChatParser(self.pathToLogs, self.room_names)
        update_splash_window_info("Setup worker threads")
        self._setupThreads()
        update_splash_window_info("Setup UI")
        self._wireUpUIConnections()
        update_splash_window_info("Recall cached settings")
        self._recallCachedSettings()

        self._startStatisticTimer()
        update_splash_window_info("Fetch data from eve-scout.com")
        self._wireUpDatabaseViews()

        self.blockSignals(False)
        update_splash_window_info("Start all worker threads")
        self._startThreads()
        self.changeRegionByName(region_name=region_name)
        self.updateSidePanel()

        update_splash_window_info("Apply theme.")

        initial_theme = self.cache.getFromCache("theme")
        if initial_theme:
            self.changeTheme(initial_theme)

        update_splash_window_info("Double check for updates on github...")
        update_avail = evegate.checkSpyglassVersionUpdate()
        if update_avail[0]:
            logging.info(update_avail[1])
            update_splash_window_info("There is a updates available. {}".format(update_avail[1]))
            self.ui.updateAvail.show()
            self.ui.updateAvail.setText(update_avail[1])

            def openDownloadLink():
                QDesktopServices.openUrl(evegate.getSpyglassUpdateLink())
                self.ui.updateAvail.hide()
                self.ui.updateAvail.disconnect(openDownloadLink)
            self.ui.updateAvail.clicked.connect(openDownloadLink)
        else:
            logging.info(update_avail[1])
            update_splash_window_info(update_avail[1])
            self.ui.updateAvail.hide()
        update_splash_window_info("EVE-Syp perform an initial scan of all intel files.")
        self.rescanIntel()
        update_splash_window_info("Initialisation succeeded.")
        self.tool_widget = None

    @property
    def systems_on_map(self) -> dict[str, System]:
        return self.dotlan.systems

    @property
    def systemsById(self) -> dict[int, System]:
        return self.dotlan.systemsById

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
        self.actions_pack.framelessCheck.triggered.connect(self.trayIcon.changeFrameless)
        self.actions_pack.alarmCheck.triggered.connect(self.trayIcon.switchAlarm)
        self.actions_pack.quitAction.triggered.connect(self.trayIcon.quit)

    def _updateKnownPlayerAndMenu(self, names=None):
        """
        Updates the players menu
        Args:
            names:

        Returns:

        """
        known_player_names = self.knownPlayerNames

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

        self.updateSidePanel()

    def _addPlayerMenu(self):
        self.playerGroup = QActionGroup(self.ui.menu)
        self.playerGroup.setExclusionPolicy(QActionGroup.ExclusionPolicy.None_)
        self.ui.menuChars.clear()
        for name in self.knownPlayerNames:
            icon = QIcon()
            if evegate.esiCheckCharacterToken(name):
                avatar_raw_img = evegate.esiCharactersPortrait(name)
                if avatar_raw_img is not None:
                    icon.addPixmap(QPixmap.fromImage(QImage.fromData(avatar_raw_img)))
            action = QAction(icon, "{0}".format(name))
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

    def wheelDirChanged(self, checked):
        self.invertWheel = checked
        if self.invertWheel:
            self.ui.mapView.wheel_dir = -1.0
        else:
            self.ui.mapView.wheel_dir = 1.0
        self.ui.actionInvertMouseWheel.setChecked(self.invertWheel)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        painter.end()

    def _recallCachedSettings(self):
        try:
            self.cache.recallAndApplySettings(self, "settings")
        except Exception as e:
            logging.error(e)

    def changeAutoRegion(self, auto_change: bool):
        self.autoChangeRegion = auto_change

    def _wireUpUIConnections(self):
        logging.info("wireUpUIConnections")
        self.clipboard.dataChanged.connect(self.clipboardChanged)
        self.ui.statisticsButton.clicked.connect(self.changeStatisticsVisibility)
        self.ui.adm_vul_Button.clicked.connect(self.changeADMVisibility)
        self.ui.jumpbridgesButton.clicked.connect(self.changeJumpbridgesVisibility)
        self.ui.infoAction.triggered.connect(self.showInfo)
        self.ui.showChatAvatarsAction.triggered.connect(self.changeShowAvatars)
        self.ui.alwaysOnTopAction.triggered.connect(self.changeAlwaysOnTop)
        self.ui.chooseChatRoomsAction.triggered.connect(self.showChatroomChooser)
        self.ui.catchRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.catchRegionAction))
        self.ui.providenceRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.providenceRegionAction))
        self.ui.queriousRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.queriousRegionAction))
        self.ui.providenceCatchRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.providenceCatchRegionAction))
        self.ui.providenceCatchCompactRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.providenceCatchCompactRegionAction))
        self.ui.wickedcreekScaldingpassRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.ui.wickedcreekScaldingpassRegionAction))
        self.ui.showChatAction.triggered.connect(self.changeChatVisibility)
        self.ui.soundSetupAction.triggered.connect(self.showSoundSetup)
        self.ui.activateSoundAction.triggered.connect(self.changeSound)
        self.ui.useSpokenNotificationsAction.triggered.connect(self.changeUseSpokenNotifications)
        self.trayIcon.alarm_distance.connect(self.changeAlarmDistance)
        self.ui.framelessWindowAction.triggered.connect(self.changeFrameless)
        self.trayIcon.change_frameless.connect(self.changeFrameless)
        self.ui.frameButton.clicked.connect(self.changeFrameless)
        self.ui.quitAction.triggered.connect(self.close)
        self.trayIcon.quit_signal.connect(self.close)
        self.ui.jumpbridgeDataAction.triggered.connect(self.showJumpbridgeChooser)
        self.ui.rescanNowAction.triggered.connect(self.rescanIntel)
        self.ui.clearIntelAction.triggered.connect(self.clearIntelChat)
        self.ui.mapView.webViewUpdateScrollbars.connect(self.fixupScrollBars)
        self.ui.mapView.webViewNavigateBackward.connect(self.navigateBack)
        self.ui.mapView.customContextMenuRequested.connect(self.showMapContextMenu)

        def indexChanged():
            if hasattr(self, "statisticsThread"):
                self.statisticsThread.fetchLocation(fetch=False)
            new_region_name = str(self.ui.regionNameField.currentText())
            if new_region_name in [region["name"] for region in Universe.REGIONS]:
                self.changeRegionByName(region_name=new_region_name)

        self.ui.regionNameField.currentIndexChanged.connect(indexChanged)
        self.ui.regionNameField.addItems(sorted([region["name"] for region in Universe.REGIONS]))
        self.region_changed.connect(
            lambda rgn_str: self.ui.regionNameField.setCurrentText(rgn_str))

        def mapviewIsScrolling(scrolled_active):
            if scrolled_active:
                self.mapTimer.stop()
            else:
                curr_region_name = self.cache.getFromCache("region_name")
                curr_pos = self.ui.mapView.scrollPosition()
                curr_zoom = self.ui.mapView.zoomFactor()
                self.region_queue.enqueue((curr_region_name, curr_pos, curr_zoom))
                self.mapTimer.start(MAP_UPDATE_INTERVAL_MSEC)

        self.ui.mapView.webViewIsScrolling.connect(mapviewIsScrolling)
        self.ui.connectToEveOnline.clicked.connect(
            lambda:
                self._updateKnownPlayerAndMenu(evegate.openWithEveonline(parent=self)))

        def updateX(x: float):
            pos = self.ui.mapView.scrollPosition()
            pos.setX(x)
            self.ui.mapView.setScrollPosition(pos)
        self.ui.mapHorzScrollBar.valueChanged.connect(updateX)

        def updateY(y: float):
            pos = self.ui.mapView.scrollPosition()
            pos.setY(y)
            self.ui.mapView.setScrollPosition(pos)
        self.ui.mapVertScrollBar.valueChanged.connect(updateY)

        def hoveCheck(global_pos: QPoint, pos: QPoint) -> bool:
            """
                Figure out if a system is below the mouse position
                using QtWidgets.QToolTip to popup system relate information on screen
            Args:
                global_pos: global position
                pos: position related to the svg

            Returns: true if the mouse is above a system, else false
            """
            for system in self.systems_on_map.values():
                if system.mapCoordinates.contains(pos):
                    if not QtWidgets.QToolTip.isVisible():
                        QtWidgets.QToolTip.showText(global_pos, system.getTooltipText(), self)
                    return True
            return False

        self.ui.mapView.hoveCheck = hoveCheck

        def doubleClicked(pos: QPoint):
            for name, system in self.systems_on_map.items():
                if system.mapCoordinates.contains(pos):
                    self.mapLinkClicked(QtCore.QUrl("map_link/{0}".format(name)))
                    break
        self.ui.mapView.doubleClicked = doubleClicked

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
            if self.ui.actionUserTheraRoutes.isChecked():
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

    def updateSidePanel(self):
        return
        inx_poi = self.ui.qSidepannel.indexOf(self.ui.qTabPOIS)
        inx_jumpbridges = self.ui.qSidepannel.indexOf(self.ui.qTabJumpbridges)
        if evegate.esiCharName() is None:
            self.ui.qSidepannel.setTabVisible(inx_poi, False)
            self.ui.qSidepannel.setTabVisible(inx_jumpbridges, False)
        else:
            self.ui.qSidepannel.setTabVisible(inx_poi, True)
            self.ui.qSidepannel.setTabVisible(inx_jumpbridges, True)

    def _wireUpDatabaseViewPOI(self):
        model = POITableModell()

        def callPOIUpdate():
            model.setQuery("SELECT type as Type, name as Name FROM pointofinterest")
            self.ui.tableViewPOIs.resizeColumnsToContents()
            self.ui.tableViewPOIs.resizeRowsToContents()

        self.ui.tableViewPOIs.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.tableViewPOIs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tableViewPOIs.setDragEnabled(True)
        self.ui.tableViewPOIs.setAcceptDrops(True)
        self.ui.tableViewPOIs.setDropIndicatorShown(True)
        self.ui.tableViewPOIs.setDragDropOverwriteMode(False)

        self.ui.tableViewPOIs.setDragDropMode(QAbstractItemView.InternalMove)
        self.ui.tableViewPOIs.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.ui.tableViewPOIs.setDefaultDropAction(Qt.MoveAction)
        # callPOIUpdate()
        sort = QSortFilterProxyModel()
        sort.setSourceModel(model)
        self.tableViewPOIsDelegate = StyledItemDelegatePOI(self)
        self.tableViewPOIsDelegate.poi_edit_changed.connect(callPOIUpdate)
        self.ui.tableViewPOIs.setModel(sort)
        self.ui.tableViewPOIs.setItemDelegate(self.tableViewPOIsDelegate)
        self.ui.tableViewPOIs.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.ui.tableViewPOIs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tableViewPOIs.resizeColumnsToContents()
        self.ui.tableViewPOIs.resizeRowsToContents()

        self.poi_changed.connect(callPOIUpdate)
        self.ui.tableViewPOIs.show()
        callPOIUpdate()

        def showPOIContextMenu(pos):
            index = self.ui.tableViewPOIs.model().mapToSource(self.ui.tableViewPOIs.indexAt(pos)).row()
            item = self.cache.getPOIAtIndex(index)
            if "solar_system_id" in item:
                lps_ctx_menu = POIContextMenu(system_name=Universe.systemNameById(item["solar_system_id"]))
            elif "system_id" in item:
                lps_ctx_menu = POIContextMenu(system_name=Universe.systemNameById(item["system_id"]))
            else:
                lps_ctx_menu = POIContextMenu()

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
                    if "solar_system_id" in item:
                        self.region_changed_by_system_id.emit(int(item["solar_system_id"]))
                    elif "system_id" in item:
                        self.region_changed_by_system_id.emit(int(item["system_id"]))
                    return

        self.ui.tableViewPOIs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableViewPOIs.customContextMenuRequested.connect(showPOIContextMenu)

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
            self.ui.lineEditThera.setText(system_name)
            self.ui.tableViewThera.model().sourceModel().updateData(system_name)

        def theraSystemChanged():
            sys_name = self.ui.lineEditThera.text()
            self.cache.putIntoCache("thera_source_system", sys_name)
            self.ui.tableViewThera.model().sourceModel().updateData(sys_name)

        self.ui.lineEditThera.editingFinished.connect(theraSystemChanged)
        # self.ui.actionUserTheraRoutes.toggled.connect(theraSystemChanged)

        def showTheraContextMenu(pos):
            menu_inx = self.ui.tableViewThera.model().mapToSource(self.ui.tableViewThera.indexAt(pos))
            item = self.ui.tableViewThera.model().sourceModel().thera_data[menu_inx.row()]

            if menu_inx.column() == 8:
                target_system_name = item["out_system_name"]
            else:
                target_system_name = item["in_system_name"]

            lps_ctx_menu = TheraContextMenu(target_system_name)
            lps_ctx_menu.setStyleSheet(Styles.getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewPOIs.mapToGlobal(pos))
            if self.handleDestinationActions(act=res, destination={"system_id": Universe.systemIdByName(target_system_name)}):
                return
            elif res == lps_ctx_menu.updateData:
                self.ui.tableViewThera.model().sourceModel().updateData()
                return
            elif res == lps_ctx_menu.selectRegion:
                self.region_changed_by_system_id.emit(Universe.systemIdByName(target_system_name))
                return

        self.ui.tableViewThera.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableViewThera.customContextMenuRequested.connect(showTheraContextMenu)

    def _wireUpDatabaseViewsJB(self):
        model = QSqlQueryModel()

        def callOnUpdate():
            self.mapJumpGates = self.cache.getJumpGates()
            if self.dotlan:
                self.dotlan.setJumpbridges(self.mapJumpGates)
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
                    QApplication.processEvents()
                return
            elif res == lps_ctx_menu.delete:
                inx_selected = self.ui.tableViewJBs.selectedIndexes()
                items = dict()
                for inx in inx_selected:
                    items[inx.row()] = self.cache.getJumpGatesAtIndex(inx.row())
                for item in items.values():
                    self.cache.clearJumpGate(item["src"])
                    self.jbs_changed.emit()
                    QApplication.processEvents()
                return
            elif res == lps_ctx_menu.selectRegionSrc:
                items = dict()
                inx_selected = self.ui.tableViewJBs.selectedIndexes()
                for inx in inx_selected:
                    items[inx.row()] = self.cachegetJumpGatesAtIndex(inx.row())
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

        self.ui.tableViewStorm.model().sourceModel().updateData()

        def showStormContextMenu(pos):
            menu_inx = self.ui.tableViewStorm.model().mapToSource(self.ui.tableViewStorm.indexAt(pos))
            item = self.ui.tableViewStorm.model().sourceModel().model_data[menu_inx.row()]

            target_system_name = item["system_name"]

            lps_ctx_menu = TheraContextMenu(target_system_name)
            lps_ctx_menu.setStyleSheet(Styles.getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewPOIs.mapToGlobal(pos))
            if self.handleDestinationActions(act=res, destination={"system_id": Universe.systemIdByName(target_system_name)}):
                return
            elif res == lps_ctx_menu.updateData:
                self.ui.tableViewStorm.model().sourceModel().updateData()
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
            self.rescanIntel()
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
            self.focusMapOnSystem(system_id)

    def _setupThreads(self):
        logging.info("Set up threads and their connections...")
        self.avatarFindThread = AvatarFindThread()
        self.avatarFindThread.avatar_update.connect(self.updateAvatarOnChatEntry)

        self.filewatcherThread = filewatcher.FileWatcher(self.pathToLogs)
        self.filewatcherThread.file_change.connect(self.logFileChanged)

        self.statisticsThread = MapStatisticsThread()
        self.statisticsThread.statistic_data_update.connect(self.updateStatisticsOnMap)

        self.zkillboard = Zkillmonitor(parent=self)
        self.zkillboard.report_system_kill.connect(self.updateKillboard)
        self.zkillboard.status_killmail.connect(lambda online: self.ui.m_qLedZKillboarOnline.setPixmap(
                    QPixmap(u":/Icons/res/online.svg" if online else QPixmap(u":/Icons/res/offline.svg"))))

        self.apiThread = None

        #  self.filewatcherThread.addMonitorFile(zkillMonitor.MONITORING_PATH)
        logging.info("Set up threads and their connections done.")

    def _startThreads(self):
        self.avatarFindThread.start()
        self.filewatcherThread.start()
        self.statisticsThread.start()
        self.zkillboard.startConnect()

    def _terminateThreads(self):
        logging.info("Stop the threads ...")
        try:
            self.zkillboard.startDisconnect()
            SoundManager().quit()
            SoundManager().wait()
            self.avatarFindThread.quit()
            self.avatarFindThread.wait()
            self.filewatcherThread.quit()
            self.filewatcherThread.wait()
            self.statisticsThread.quit()
            self.statisticsThread.wait()
            self.mapTimer.stop()
            if self.apiThread:
                self.apiThread.quit()
                self.apiThread.wait()
            logging.info("Stop the threads done.")
        except Exception as ex:
            logging.critical(ex)
            pass

    def changeRegionFromCtxMenu(self):
        selected_system = self.trayIcon.contextMenu().currentSystem
        if selected_system is None:
            return
        self.ui.regionNameField.setCurrentText(selected_system.name)
        # self.changeRegionBySystemID(selected_system.system_id)

    def focusMapOnSystem(self, system_id: int):
        """sets the system defined by the id to the focus of the map
        """
        # todo call via emit
        if system_id is None:
            return
        if system_id in self.systemsById:
            selected_system = self.systemsById[system_id]
            view_center = self.ui.mapView.size() / 2
            pt_system = QPointF(selected_system.mapCoordinates.center().x()
                                * self.ui.mapView.zoom-view_center.width(),
                                selected_system.mapCoordinates.center().y()
                                * self.ui.mapView.zoom-view_center.height())
            self.ui.mapView.setScrollPosition(pt_system)

    def navigateBack(self, back):
        """
        Implements the backward forward mouse key functions
        Args:
            back: True mean back els forward

        Returns:

        """
        if back:
            region_name, pos, zoom = self.region_queue.undo()
        else:
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
        curr_region_name = self.cache.getFromCache("region_name")
        if curr_region_name == region_name:
            return
        if update_queue:
            curr_pos = self.ui.mapView.scrollPosition()
            curr_zoom = self.ui.mapView.zoomFactor()
            self.region_queue.enqueue((curr_region_name, curr_pos, curr_zoom))

        self.cache.putIntoCache("region_name", region_name)
        self.setupMap()
        if update_queue:
            if system_id is not None:
                self.focusMapOnSystem(system_id)
            else:
                view_center = self.ui.mapView.size() / 2
                size_of_image = self.ui.mapView.imgSize
                pt_system = QPointF(size_of_image.width()/2.0
                                    * self.ui.mapView.zoom - view_center.width(),
                                    size_of_image.height()/2.0
                                    * self.ui.mapView.zoom - view_center.height())
                self.ui.mapView.setScrollPosition(pt_system)
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
            Reads the regions svg content in order filesystem, cache or dotlan
        Args:
            cache:
            region_name:

        Returns:

        """
        res_file_name = os.path.join("vi", "ui", "res", "mapdata", "{0}.svg".format(
            evegate.convertRegionNameForDotlan(region_name)))
        if resourcePathExists(res_file_name):
            with open(resourcePath(res_file_name)) as svgFile:
                svg = svgFile.read()
                return svg
        else:
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

    def setupMap(self):
        logging.debug("setupMap started...")
        region_name = self.cache.getFromCache("region_name")
        if not region_name:
            region_name = "Providence"

        if False and region_name in self.dotlan_maps:
            self.dotlan = self.dotlan_maps[region_name]
        else:
            svg = self.loadSVGMapFile(self.cache, region_name)
            if svg is None:
                return
            self.dotlan_maps[region_name] = self.dotlan = dotlan.Map(
                region_name=region_name,
                svg_file=svg,
                set_jump_maps_visible=self.ui.jumpbridgesButton.isChecked(),
                set_statistic_visible=self.ui.statisticsButton.isChecked(),
                set_jump_bridges=self.mapJumpGates)
            if self.dotlan:
                self.dotlan.setTheraConnections(evegate.ESAPIListPublicSignatures())

            self.dotlan = self.dotlan_maps[region_name]

        if self.dotlan.outdatedCacheError:
            e = self.dotlan.outdatedCacheError
            diag_text = "Something went wrong getting map data. Proceeding with older cached data. " \
                        "Check for a newer version and inform the maintainer.\n\nError: {0} {1}".format(type(e), str(e))
            logging.warning(diag_text)
            QMessageBox.warning(self, "Using map from cache", diag_text, QMessageBox.Ok)

        # Update the new map view, then clear old statistics from the map and request new
        logging.debug("Updating the map")
        self.updateMapView()
        self.setInitialMapPositionForRegion(region_name)
        self.mapTimer.start(MAP_UPDATE_INTERVAL_MSEC)
        # Allow the file watcher to run now that all else is set up
        logging.debug("setupMap succeeded.")

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

            # todo: send location not in all cases
            self.statisticsThread.requestLocations()
            self.updateMapView()
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

        self.statisticsThread.requestLocations()
        self.statisticsThread.requestStatistics()
        self.statisticsThread.requestSovereignty()

    def closeEvent(self, event):
        """
            Persisting things to the cache before closing the window
        """
        # Program state to cache (to read it on next startup)
        settings = ((None, "restoreGeometry", str(self.saveGeometry()), True),
                    (None, "restoreState", str(self.saveState()), True),
                    ("ui.splitter", "restoreGeometry", str(self.ui.splitter.saveGeometry()), True),
                    ("ui.splitter", "restoreState", str(self.ui.splitter.saveState()), True),
                    ("ui.mapView", "setZoomFactor", self.ui.mapView.zoomFactor()),
                    # ("ui.qSidepannel", "restoreGeometry", str(self.ui.qSidepannel.saveGeometry()), True),
                    (None, "changeChatFontSize", ChatEntryWidget.TEXT_SIZE),
                    (None, "setOpacity", self.opacityGroup.checkedAction().opacity),
                    (None, "changeAlwaysOnTop", self.ui.alwaysOnTopAction.isChecked()),
                    (None, "changeShowAvatars", self.ui.showChatAvatarsAction.isChecked()),
                    (None, "changeAlarmDistance", self.alarmDistance),
                    (None, "changeSound", self.ui.activateSoundAction.isChecked()),
                    (None, "changeChatVisibility", self.ui.showChatAction.isChecked()),
                    (None, "loadInitialMapPositions", self.mapPositionsDict),
                    (None, "setSoundVolume", SoundManager().soundVolume),
                    (None, "changeFrameless", self.ui.framelessWindowAction.isChecked()),
                    (None, "changeUseSpokenNotifications", self.ui.useSpokenNotificationsAction.isChecked()),
                    (None, "changeAutoChangeRegion", self.autoChangeRegion),
                    (None, "wheelDirChanged", self.invertWheel),
                    (None, "showJumpbridge", self.ui.jumpbridgesButton.isChecked()),
                    (None, "showStatistic", self.ui.statisticsButton.isChecked()),
                    (None, "setIntelTime", Globals().intel_time))

        self.cache.putIntoCache("version", str(vi.version.VERSION), 60 * 60 * 24 * 30)
        self.cache.putIntoCache("settings", str(settings), 60 * 60 * 24 * 30)
        self._terminateThreads()
        self.trayIcon.hide()
        event.accept()
        QtCore.QCoreApplication.quit()

    def changeChatVisibility(self, value=None):
        if value is None:
            value = self.ui.showChatAction.isChecked()
        self.ui.showChatAction.setChecked(value)
        # self.ui.chatbox.setVisible(value)

    def changeAutoChangeRegion(self, value=None):
        if value is None:
            value = self.ui.actionAuto_switch.isChecked()
        self.ui.actionAuto_switch.setChecked(value)
        self.autoChangeRegion = value


    def changeUseSpokenNotifications(self, value=None):
        if SoundManager().platformSupportsSpeech():
            if value is None:
                value = self.ui.useSpokenNotificationsAction.isChecked()
            self.ui.useSpokenNotificationsAction.setChecked(value)
            SoundManager().setUseSpokenNotifications(value)
        else:
            self.ui.useSpokenNotificationsAction.setChecked(False)
            self.ui.useSpokenNotificationsAction.setEnabled(False)

    def setIntelTime(self, minutes=None):
        if minutes and self.intelTimeGroup:
            for action in self.intelTimeGroup.actions():
                action.setChecked(action.intelTime == minutes)
        Globals().intel_time = minutes
        self.ui.timeInfo.setText("All Intel (past {} minutes)".format(Globals().intel_time))

    def changeIntelTime(self):
        action = self.intelTimeGroup.checkedAction()
        Globals().intel_time = action.intelTime
        self.ui.timeInfo.setText("All Intel (past {} minutes)".format(Globals().intel_time))
        self.rescanIntel()

    def setOpacity(self, value=None):
        if value:
            for action in self.opacityGroup.actions():
                action.setChecked(action.opacity == value)
        action = self.opacityGroup.checkedAction()
        self.setWindowOpacity(action.opacity)

    def changeOpacity(self):
        action = self.opacityGroup.checkedAction()
        self.setWindowOpacity(action.opacity)

    def changeTheme(self, th=None):
        logging.info("change theme")
        if th is not None:
            for action in self.themeGroup.actions():
                if action.theme == th:
                    action.setChecked(True)
        action = self.themeGroup.checkedAction()
        styles = Styles()
        styles.setStyle(action.theme)
        theme = styles.getStyle()
        self.setStyleSheet(theme)
        self.trayIcon.contextMenu().setStyleSheet(theme)
        logging.info("Setting new theme: {}".format(action.theme))
        self.cache.putIntoCache("theme", action.theme, 60 * 60 * 24 * 365)

    def changeSound(self, value=None, disable=False):
        if disable:
            self.ui.activateSoundAction.setChecked(False)
            self.ui.activateSoundAction.setEnabled(False)
            self.ui.useSpokenNotificationsAction(False)
            self.ui.soundSetupAction.setEnabled(False)
            QMessageBox.warning(
                self, "Sound disabled",
                "The lib 'pyglet' which is used to play sounds cannot be found, ""so the soundsystem is disabled.\n"
                "If you want sound, please install the 'pyglet' library. This warning will not be shown again.",
                QMessageBox.Ok)
        else:
            if value is None:
                value = self.ui.activateSoundAction.isChecked()
            self.ui.activateSoundAction.setChecked(value)
            SoundManager().soundActive = value

    def changeAlwaysOnTop(self, value=None):
        if value is None:
            value = self.ui.alwaysOnTopAction.isChecked()
        do_show = self.isVisible()
        if do_show:
            self.hide()
        self.ui.alwaysOnTopAction.setChecked(value)
        if value:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & (~Qt.WindowStaysOnTopHint))
        if do_show:
            self.show()

    def changeFrameless(self, value=None):
        if value is None:
            value = not self.ui.frameButton.isVisible()
        do_show = self.isVisible()
        if do_show:
            self.hide()
        if value:
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.changeAlwaysOnTop(True)
        else:
            self.setWindowFlags(self.windowFlags() & (~Qt.FramelessWindowHint))
        self.ui.menubar.setVisible(not value)
        self.ui.frameButton.setVisible(value)
        self.ui.framelessWindowAction.setChecked(value)

        for cm in TrayContextMenu.instances:
            cm.framelessCheck.setChecked(value)

        if do_show:
            self.show()

    def changeShowAvatars(self, value=None):
        if value is None:
            value = self.ui.showChatAvatarsAction.isChecked()
        self.ui.showChatAvatarsAction.setChecked(value)
        ChatEntryWidget.SHOW_AVATAR = value
        for entry in self.chatEntries:
            entry.ui.avatarLabel.setVisible(value)

    def changeChatFontSize(self, font_size):
        if font_size:
            ChatEntryWidget.TEXT_SIZE = font_size
            for entry in self.chatEntries:
                entry.changeFontSize(font_size)

    def chatSmaller(self):
        new_size = ChatEntryWidget.TEXT_SIZE - 1
        self.changeChatFontSize(new_size)

    def chatLarger(self):
        new_size = ChatEntryWidget.TEXT_SIZE + 1
        self.changeChatFontSize(new_size)

    def changeAlarmDistance(self, distance):
        for system in ALL_SYSTEMS.values():
            system.changeIntelRange(old_intel_range=self.alarmDistance, new_intel_range=distance)
        self.alarmDistance = distance
        for cm in TrayContextMenu.instances:
            for action in cm.distanceGroup.actions():
                if action.alarmDistance == distance:
                    action.setChecked(True)
        self.trayIcon.alarmDistance = distance

    def changeJumpbridgesVisibility(self, val):
        self.dotlan.changeJumpbridgesVisibility(val)
        self.updateMapView()

    def changeADMVisibility(self, val):
        self.dotlan.changeVulnerableVisibility(val)
        self.updateMapView()

    def changeStatisticsVisibility(self, val):
        self.dotlan.changeStatisticsVisibility(val)
        self.updateMapView()

    def clipboardChanged(self):
        """ the content of the clip board is used to set jump bridge and poi
        """
        clip_content = self.clipboard.text()
        if clip_content != self.oldClipboardContent:
            for full_line_content in clip_content.splitlines():
                for line_content in tokenize_eve_formatted_text(full_line_content):
                    cb_type, cb_data = evaluateClipboardData(line_content)
                    if cb_type == "poi":
                        if self.cache.putPOI(cb_data):
                            self.poi_changed.emit()
                    elif cb_type == "jumpbridge":
                        if self.cache.putJumpGate(
                                src=cb_data["src"],
                                dst=cb_data["dst"],
                                src_id=cb_data["id_src"],
                                dst_id=cb_data["id_dst"],
                                json_src=cb_data["json_src"],
                                json_dst=cb_data["json_dst"]):
                            self.jbs_changed.emit()
                    elif cb_type == "link":
                        QDesktopServices.openUrl(cb_data)
            self.oldClipboardContent = clip_content

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
            if system_marked in self.systems_on_map.keys():
                curr_sys = self.systems_on_map[system_marked]
                curr_sys.mark()
                self.focusMapOnSystem(curr_sys.system_id)
            else:
                self.statisticsThread.fetchLocation(fetch=False)
                self.changeRegionBySystemID(Universe.systemIdByName(system_marked))
        elif type(system_marked) is int:
            if system_marked in self.systemsById:
                curr_sys = self.systemsById[system_marked]
                curr_sys.mark()
                self.focusMapOnSystem(curr_sys.system_id)
            else:
                self.statisticsThread.fetchLocation(fetch=False)
                self.changeRegionBySystemID(system_marked)
                curr_sys = self.systemsById[system_marked]
                curr_sys.mark()
        elif type(system_marked) is System:
            system_marked.mark()
            self.focusMapOnSystem(system_marked.system_id)
        self.updateMapView()

    def updateCharLocationOnMap(self, system_id: int, char_name: str) -> None:
        """
            Remove the char on all maps, then assign to the system with id system_is
        Args:
            system_id:
            char_name:

        Returns:

        """
        for system in ALL_SYSTEMS.values():
            system.removeLocatedCharacter(char_name, self.alarmDistance)

        if system_id in ALL_SYSTEMS.keys():
            system = ALL_SYSTEMS[system_id]
            system.addLocatedCharacter(char_name, self.alarmDistance)
            logging.info("The location of character '{}' changed to system '{}'".format(char_name, system.name))
        else:
            logging.info("The location of character '{}' changed to Unknown system.".format(char_name))

    def locateChar(self):
        self.statisticsThread.fetchLocation(fetch=True)
        self.statisticsThread.requestLocations()

    def setLocation(self, char_name, system_in, change_region: bool = False) -> None:
        """
        Change the location of the char to the given system inside the current map, if required the region may be
        changed. If the character is api registered, the actual system will be shown in the center of the screen.

        Args:
            char_name: name of the character
            system_in: system name
            change_region: allow change of the region

        Returns:
            None:
        """
        system_id = system_in if type(system_in) is int else Universe.systemIdByName(system_in)
        system_name = system_in if type(system_in) is str else Universe.systemNameById(system_in)
        # self.updateCharLocationOnMap(system_id, char_name)
        if system_name not in self.systems_on_map:
            if change_region:   # and char_name in self.monitoredPlayerNames:
                try:
                    system_id = Universe.systemIdByName(system_name)
                    selected_region_name = Universe.regionNameFromSystemID(system_id)
                    concurrent_region_name = self.cache.getFromCache("region_name")
                    if selected_region_name != concurrent_region_name:
                        self.changeRegionByName(region_name=selected_region_name, system_id=system_id)
                except Exception as e:
                    logging.error(e)
                    pass
            self.updateMapView()
        elif not system_name == "?" and system_name in self.systems_on_map:
            self.updateCharLocationOnMap(system_id, char_name)
            if evegate.esiCheckCharacterToken(char_name):
                self.focusMapOnSystem(self.systems_on_map[str(system_name)].system_id)
                self.current_system_changed.emit(str(system_name))
            self.updateMapView()

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
                region_name = self.cache.getFromCache("region_name")
            if region_name and region_name in self.mapPositionsDict:
                xy = self.mapPositionsDict[region_name]
                self.initialMapPosition = QPointF(xy[0], xy[1])
            else:
                self.initialMapPosition = None
        except Exception as e:
            logging.error("Error setInitialMapPositionForRegion failed: {0}".format(str(e)))
            pass

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

    def showChatroomChooser(self):
        chooser = ChatroomChooser(self)
        chooser.rooms_changed.connect(self.changedRoomNames)
        chooser.show()

    def callOnJbUpdate(self):
        return

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

    def showStatistic(self, value):
        self.ui.statisticsButton.setChecked(value)

    def showJumpbridge(self, value):
        self.ui.jumpbridgesButton.setChecked(value)

    def callDeleteJumpbridge(self):
        self.cache.clearJumpGate(None)
        self.jbs_changed.emit()
        QApplication.processEvents()

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
                QApplication.processEvents()

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
                QApplication.processEvents()
            self.cache.putIntoCache("jumpbridge_url", url)

        except Exception as e:
            logging.error("Error setJumpbridges failed: {0}".format(str(e)))
            QMessageBox.warning(self, "Loading jumpbridges failed!", "Error: {0}".format(str(e)), QMessageBox.Ok)

    def handleRegionMenuItemSelected(self, action=None):
        self.ui.catchRegionAction.setChecked(False)
        self.ui.providenceRegionAction.setChecked(False)
        self.ui.queriousRegionAction.setChecked(False)
        self.ui.wickedcreekScaldingpassRegionAction.setChecked(False)
        self.ui.providenceCatchRegionAction.setChecked(False)
        self.ui.providenceCatchCompactRegionAction.setChecked(False)
        if action:
            action.setChecked(True)
            selected_region_name = str(action.property("regionName"))
            self.changeRegionByName(region_name=selected_region_name)

    def showRegionChooser(self):
        def handleRegionChosen(region_name):
            self.handleRegionMenuItemSelected(None)
            self.changeRegionByName(region_name=region_name)

        chooser = RegionChooser(self, region_name=self.cache.getFromCache("region_name"))
        chooser.new_region_chosen.connect(handleRegionChosen)
        chooser.show()

    @staticmethod
    def formatZKillMessage(message):
        soup = dotlan.BeautifulSoup(message)
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

    def addMessageToIntelChat(self, message: Message):
        scroll_to_bottom = False
        if self.ui.chatListWidget.verticalScrollBar().value() == self.ui.chatListWidget.verticalScrollBar().maximum():
            scroll_to_bottom = True

        if self.ui.useSpokenNotificationsAction.isChecked():
            if message.roomName == "zKillboard":
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
            # with open(resourcePath(os.path.join("vi", "ui", "res", "zKillboard.svg")), "rb") as f:
            #     avatar_icon = f.read()
        elif message.user != "zKillboard.com":
            avatar_icon = self.cache.getImageFromAvatar(message.user)
            if avatar_icon is None:
                self.avatarFindThread.addChatEntry(chat_entry_widget)
        if avatar_icon is not None:
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
            self.updateMapView()
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

    def showInfo(self):
        info_dialog = QtWidgets.QDialog(self)
        info_dialog.ui = Ui_EVESpyInfo()
        info_dialog.ui.setupUi(info_dialog)
        version_text = info_dialog.ui.versionLable.text().replace("#ver#", vi.version.VERSION)
        info_dialog.ui.versionLable.setText(version_text)
        # info_dialog.setWindowFlags(Qt.Popup or Qt.WindowTitleHint)
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
        dialog.ui.useSpokenNotifications.setChecked(self.ui.useSpokenNotificationsAction.isChecked())
        dialog.ui.useSpokenNotifications.clicked.connect(self.changeUseSpokenNotifications)
        # dialog.setWindowFlags(Qt.Popup)

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
            dialog.ui.useSpokenNotifications.setChecked(self.ui.useSpokenNotificationsAction.isChecked())

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
        Assigns the blob data as pixmap to the entry, if a pixmap coud be loaded directly,m otherwise
        the blob will be loaded wia avatar thread
        Args:
            entry: new message
            data: blob of image

        Returns:
            None: emits avatar_loaded
        """
        if entry.updateAvatar(data):
            self.avatar_loaded.emit(entry.message.user, data)
        else:
            self.avatarFindThread.addChatEntry(entry, clear_cache=True)

    def updateStatisticsOnMap(self, data):

        if "statistics" in data.keys():
            self.mapStatisticCache = data["statistics"]
            if self.dotlan:
                self.dotlan.addSystemStatistics(data['statistics'])
        if "server-status" in data.keys():
            server_status = data["server-status"]
            if server_status["players"] > 0:
                self.ui.m_qLedOnline.setPixmap(QPixmap(u":/Icons/res/online.svg"))
            else:
                self.ui.m_qLedOnline.setPixmap(QPixmap(u":/Icons/res/offline.svg"))
            self.ui.m_qPlayerOnline.setText("Players ({players}) Server version ({server_version})".format(**server_status))

        if "thera_wormhole" in data.keys():
            thera_wormhole = data["thera_wormhole"]
            if thera_wormhole and len(thera_wormhole) > 0:
                self.ui.m_qLedEveScout.setPixmap(QPixmap(u":/Icons/res/online.svg"))
            else:
                self.ui.m_qLedEveScout.setPixmap(QPixmap(u":/Icons/res/offline.svg"))
            self.dotlan.setTheraConnections(thera_wormhole)

        if "sovereignty" in data:
            self.mapSovereignty = data['sovereignty']
            if self.dotlan:
                self.dotlan.setSystemSovereignty(data['sovereignty'])

        if "structures" in data:
            if self.dotlan:
                self.dotlan.setSystemStructures(data['structures'])

        if 'incursions' in data:
            self.mapIncursions = data['incursions']
            if self.dotlan:
                self.dotlan.setIncursionSystems(data['incursions'])

        if 'campaigns' in data:
            self.mapCampaigns = data['campaigns']
            if self.dotlan:
                self.dotlan.setCampaignsSystems(data['campaigns'])

        if "registered-chars" in data:
            first_one = True
            for itm in data["registered-chars"]:
                if itm["online"] and itm["name"] == evegate.esiCharName():
                    self.setLocation(itm["name"], itm["system"]["name"],
                                     first_one and itm["name"] == evegate.esiCharName())
                    first_one = False
            if first_one:
                for itm in data["registered-chars"]:
                    if itm["online"] and itm["name"] == evegate.esiCharName():
                        self.setLocation(itm["name"], itm["system"]["name"],
                                         first_one)
                        first_one = False

        if data["result"] == "error":
            logging.error("updateStatisticsOnMap, error: {}".format(data["text"]))
        else:
            logging.debug("Map statistic update  succeeded.")

    def zoomMapIn(self):
        self.ui.mapView.zoomIn()

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
                """
                 For each system that was mentioned in the message, check for alarm distance to the current system
                 and alarm if within alarm distance.
                """
                for system in message.affectedSystems:
                    is_alarm = message.status == States.ALARM
                    if is_alarm and message.user not in self.knownPlayerNames:
                        alarm_distance = self.alarmDistance if is_alarm else 0
                        for nSystem, data in system.getNeighbours(alarm_distance).items():
                            if "distance" not in data:
                                continue
                            chars = nSystem.getLocatedCharacters()
                            if len(chars) > 0:
                                if len(self.monitoredPlayerNames.intersection(set(chars))) > 0:
                                    self.trayIcon.showNotification(
                                        message,
                                        system.name,
                                        ", ".join(chars),
                                        data["distance"])

        for name, systems in locale_to_set.items():
            self._updateKnownPlayerAndMenu(name)
            for sys_name in systems:
                self.setLocation(name, sys_name, self.autoChangeRegion)
        QApplication.processEvents()
        if not rescan:
            self.updateMapView()

    def systemUnderMouse(self, pos: QPoint) -> Optional[dotlan.System]:
        """returns the name of the system under the mouse pointer
        """
        for system in self.systems_on_map.values():
            if system.mapCoordinates.contains(pos):
                return system
        return None

    def showMapContextMenu(self, event):
        """ checks if there is a system below the mouse position, if the systems region differs from the current
            region, the menu item to change the current region is added.
        """
        selected_system = self.systemUnderMouse(self.ui.mapView.mapPosFromPoint(event))

        map_ctx_menu = MapContextMenu()
        map_ctx_menu.framelessCheck.triggered.connect(self.trayIcon.changeFrameless)
        map_ctx_menu.alarmCheck.triggered.connect(self.trayIcon.switchAlarm)
        map_ctx_menu.quitAction.triggered.connect(self.trayIcon.quit)
        map_ctx_menu.changeRegion.triggered.connect(
            lambda: self.changeRegionBySystemID(selected_system.system_id))
        map_ctx_menu.alarm_distance.connect(self.changeAlarmDistance)
        map_ctx_menu.setStyleSheet(Styles.getStyle())

        if selected_system:
            selected_region_name = Universe.regionNameFromSystemID(selected_system.system_id)
            map_ctx_menu.updateMenu(sys_name=selected_system,
                                    rgn_name=selected_region_name,
                                    alarm_distance=self.alarmDistance)
        else:
            map_ctx_menu.updateMenu(alarm_distance=self.alarmDistance)
        res = map_ctx_menu.exec_(self.mapToGlobal(QPoint(event.x(), event.y())))
        if selected_system:
            if self.handleDestinationActions(res, destination={"system_id": selected_system.system_id}):
                return
            elif res == map_ctx_menu.clearJumpGate:
                self.cache.clearJumpGate(selected_system.name)
                self.jbs_changed.emit()
                return
