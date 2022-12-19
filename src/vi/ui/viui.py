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
import sys
import time
import requests
from typing import Union
from typing import Optional

import vi.version
from vi.universe import Universe
import logging
from PySide6.QtGui import *
from PySide6 import QtGui, QtCore, QtWidgets
from PySide6.QtCore import QPoint, QPointF, QByteArray, QSortFilterProxyModel, QTimer
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtGui import QImage, QPixmap, QDesktopServices
from PySide6.QtWidgets import QMessageBox, QStyleOption, QStyle, QFileDialog, \
    QStyledItemDelegate, QApplication, QAbstractItemView

from vi import evegate
from vi import dotlan, filewatcher
from vi import states
from vi.filewatcher import FileWatcher
from vi.ui import JumpbridgeChooser, ChatroomChooser, RegionChooser, SystemChat, ChatEntryWidget

from vi.cache.cache import Cache
from vi.resources import resourcePath, resourcePathExists
from vi.soundmanager import SoundManager
from vi.threads import AvatarFindThread, MapStatisticsThread
from vi.ui.systemtray import TrayContextMenu
from vi.ui.systemtray import JumpBridgeContextMenu
from vi.ui.systemtray import MapContextMenu
from vi.ui.systemtray import POIContextMenu
from vi.ui.systemtray import TheraContextMenu
from vi.ui.systemtray import ActionPackage
from vi.ui.styles import Styles
from vi.chatparser.chatparser import ChatParser
from vi.clipboard import evaluateClipboardData
from vi.ui.modelplayer import TableModelPlayers, StyledItemDelegatePlayers
from vi.ui.modelthera import TableModelThera
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtSql import QSqlQueryModel

from vi.ui import Ui_MainWindow, Ui_Info, Ui_SoundSetup

"""
 Timer intervals
"""
MAP_UPDATE_INTERVAL_MSEC = 1000
CLIPBOARD_CHECK_INTERVAL_MSEC = 4 * 1000


class POITableModell(QSqlQueryModel):
    def __init__(self, parent=None):
        super(POITableModell, self).__init__(parent)

    def flags(self, index) -> QtCore.Qt.ItemFlags:
        defaultFlags = super(POITableModell, self).flags(index)
        if index.isValid():
            if index.column() == 1:
                return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable | defaultFlags # | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
            else:
                return Qt.ItemIsSelectable | Qt.ItemIsEnabled | defaultFlags # | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        else:
            return Qt.ItemIsDropEnabled | defaultFlags

    def supportedDropActions(self):
        return Qt.MoveAction | Qt.CopyAction

    def dropMimeData(self, data, action, row, column, parent):
        return True

    def dropMimeData(self, data: QtCore.QMimeData, action: QtCore.Qt.DropAction, row: int, column: int, parent) -> bool:
        if action == QtCore.Qt.IgnoreAction:
            return True
        if not data.hasFormat('text/plain'):
            return False
        if column > 0:
            return False

        num_rows = self.rowCount(QtCore.QModelIndex())

        begin_row = 0
        if row != -1:
            begin_row = row
        elif parent.isValid():
            begin_row = parent.row()
        else:
            begin_row = num_rows

        if begin_row != num_rows and begin_row != 0:
            begin_row += 1

        encoded_data = data.data('text/plain')

        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
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
        mimedata = QtCore.QMimeData()
        encoded_data = QtCore.QByteArray()
        stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.WriteOnly)
        for index in indexes:
            if index.isValid():
                # src_index = self.model().mapToSource(index)
                text = json.dumps(Cache().getPOIAtIndex(index.row()))

        stream << QtCore.QByteArray(text.encode('utf-8-sig'))
        # mimedata.setData('application/json', encoded_data)
        mimedata.setData('text/plain', encoded_data)
        return mimedata


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

    def __init__(self, pat_to_logfile, tray_icon, update_splash=None):
        def update_splash_window_info(string):
            if update_splash:
                update_splash(string)

        update_splash_window_info("Init GUI application")

        QtWidgets.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(resourcePath(os.path.join("vi", "ui", "res", "eve-sso-login-black-small.png"))),
                       QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.ui.connectToEveOnline.setIcon(icon)
        self.ui.connectToEveOnline.setIconSize(QtCore.QSize(163, 38))
        self.ui.connectToEveOnline.setFlat(False)
        self.dotlan = None
        self.setWindowTitle(
            "EVE-Spy " + vi.version.VERSION + "{dev}".format(dev="-SNAPSHOT" if vi.version.SNAPSHOT else ""))
        self.taskbarIconQuiescent = QtGui.QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")))
        self.taskbarIconWorking = QtGui.QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small_green.png")))
        self.setWindowIcon(self.taskbarIconQuiescent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.pathToLogs = pat_to_logfile
        self.currContent = None
        self.mapTimer = QTimer(self)
        self.mapTimer.timeout.connect(self.updateMapView)
        self.oldClipboardContent = ""
        self.trayIcon = tray_icon
        self.trayIcon.activated.connect(self.systemTrayActivated)
        self.clipboard = QApplication.clipboard()
        self.clipboard.clear(mode=QClipboard.Mode.Clipboard)
        self.alarmDistance = 0
        self.lastStatisticsUpdate = 0
        self.chatEntries = []
        self.ui.frameButton.setVisible(False)
        self.initialMapPosition = None
        self.autoChangeRegion = False
        self.mapPositionsDict = {}
        self.mapStatisticCache = evegate.esiUniverseSystem_jumps(use_outdated=True)
        self.mapSovereignty = evegate.getPlayerSovereignty(use_outdated=True, fore_refresh=False, show_npc=True)
        self.mapIncursions = evegate.esiIncursions(use_outdated=True)
        self.mapCampaigns = evegate.esiSovereigntyCampaigns(use_outdated=True)
        self.mapJumpGates = Cache().getJumpGates()
        self.setupMap()
        self.invertWheel = False
        self._connectActionPack()

        update_splash_window_info("Preset application")

        # Set up Theme menu - fill in list of themes and add connections
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
        styles = None

        # Load user's toon names
        for api_char_names in Cache().getAPICharNames():
            if evegate.esiCharactersOnline(api_char_names):
                self._updateKnownPlayerAndMenu(api_char_names)

        if len(self.knownPlayerNames) == 0:
            diag_text = "Spyglass scans EVE system logs and remembers your characters as they change systems.\n\n" \
                        "Some features (clipboard KOS checking, alarms, etc.) may not work until your character(s)" "" \
                        "have been registered. Change systems, with each character you want to monitor, while " \
                        "Spyglass is running to remedy this."
            QMessageBox.warning(self, "Known Characters not Found", diag_text)
        update_splash_window_info("Update player names")

        if self.invertWheel is None:
            self.invertWheel = False
        self.ui.actionInvertMouseWheel.triggered.connect(self.wheelDirChanged)
        self.ui.actionInvertMouseWheel.setChecked(self.invertWheel)
        self._addPlayerMenu()
        self.players_changed.connect(self._addPlayerMenu)

        # Set up user's intel rooms
        update_splash_window_info("Set up user's intel rooms")

        cached_room_name = Cache().getFromCache("room_names")
        if cached_room_name:
            cached_room_name = cached_room_name.split(",")
        else:
            cached_room_name = ChatroomChooser.DEFAULT_ROOM_MANES
            Cache().putIntoCache("room_names", u",".join(cached_room_name), 60 * 60 * 24 * 365 * 5)
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
        self.intelTimeGroup.intelTime = 20
        for i in (10, 20, 40, 60):
            action = QAction("Past {0}min".format(i), None)
            action.setCheckable(True)
            action.setChecked(i == self.intelTimeGroup.intelTime)
            action.intelTime = i
            action.triggered.connect(self.changeIntelTime)
            self.intelTimeGroup.addAction(action)
            self.ui.menuTime.addAction(action)

        self.ui.actionAuto_switch.triggered.connect(self.changeAutoRegion)

        update_splash_window_info("Update chat parser")
        self.chatparser = ChatParser(self.pathToLogs, self.room_names, self.intelTimeGroup.intelTime)
        self._wireUpUIConnections()
        self._recallCachedSettings()
        self._setupThreads()
        self._startStatisticTimer()
        self._wireUpDatabaseViews()
        self.updateSidePanel()
        update_splash_window_info("Apply theme.")

        initial_theme = Cache().getFromCache("theme")
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
        update_splash_window_info("Rescan the intel files.")
        self.rescanIntel()
        update_splash_window_info("Initialisation succeeded.")

    @property
    def systems(self):
        return self.dotlan.systems

    @property
    def systemsById(self):
        return self.dotlan.systemsById

    @property
    def monitoredPlayerNames(self):
        return Cache().getActivePlayerNames()

    @property
    def knownPlayerNames(self):
        return Cache().getKnownPlayerNames()

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
            Cache().setKnownPlayerNames(known_player_names)
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

    def changeMonitoredPlayerNamesFromMenu(self, use):
        """
            Updates the monitoredPlayerNames set from the menu
        Args:
            use:

        Returns:
            None
        """
        player_used = set()
        for action in self.playerGroup.actions():
            action.setIconVisibleInMenu(action.isChecked())
            if action.isChecked():
                player_used.add(action.playerName)
        Cache().setActivePlayerNames(player_used)
        self.players_changed.emit()

    def wheelDirChanged(self, checked):
        self.invertWheel = checked
        if self.invertWheel:
            self.ui.mapView.wheel_dir = -1.0
        else:
            self.ui.mapView.wheel_dir = 1.0
        self.ui.actionInvertMouseWheel.setChecked(self.invertWheel)

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        painter.end()

    def _recallCachedSettings(self):
        try:
            Cache().recallAndApplySettings(self, "settings")
        except Exception as e:
            logging.error(e)

    def changeAutoRegion(self, auto_change: bool):
        self.autoChangeRegion = auto_change

    def _wireUpUIConnections(self):
        logging.info("wireUpUIConnections")
        self.clipboard.dataChanged.connect(self.clipboardChanged)
        # self.autoScanIntelAction.triggered.connect(self.changeAutoScanIntel)
        self.ui.zoomInButton.clicked.connect(self.zoomMapIn)
        self.ui.zoomOutButton.clicked.connect(self.zoomMapOut)
        self.ui.statisticsButton.clicked.connect(self.changeStatisticsVisibility)
        self.ui.jumpbridgesButton.clicked.connect(self.changeJumpbridgesVisibility)
        self.ui.chatLargeButton.clicked.connect(self.chatLarger)
        self.ui.chatSmallButton.clicked.connect(self.chatSmaller)
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
        self.ui.chooseRegionAction.triggered.connect(self.showRegionChooser)
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
        self.ui.mapView.webViewResized.connect(self.fixupScrollBars)
        self.ui.mapView.customContextMenuRequested.connect(self.showMapContextMenu)

        def mapviewScrolled(scrolled):
            if scrolled:
                self.mapTimer.stop()
            else:
                self.mapTimer.start(MAP_UPDATE_INTERVAL_MSEC)
        self.ui.mapView.webViewScrolled.connect(mapviewScrolled)
        self.ui.connectToEveOnline.clicked.connect(
            lambda:
                self._updateKnownPlayerAndMenu(evegate.openWithEveonline(parent=self)))

        def updateX(x):
            pos = self.ui.mapView.scrollPosition()
            pos.setX(x)
            self.ui.mapView.setScrollPosition(pos)
        self.ui.mapHorzScrollBar.valueChanged.connect(updateX)

        def updateY(y):
            pos = self.ui.mapView.scrollPosition()
            pos.setY(y)
            self.ui.mapView.setScrollPosition(pos)
        self.ui.mapVertScrollBar.valueChanged.connect(updateY)

        def hoveCheck(pos: QPoint) -> bool:
            """returns true if the mouse is above a system, else false
            """
            for name, system in self.systems.items():
                val = system.mapCoordinates
                rc = QtCore.QRectF(val["x"], val["y"], val["width"], val["height"])
                if rc.contains(pos):
                    return True
            return False
        self.ui.mapView.hoveCheck = hoveCheck

        def doubleClicked(pos: QPoint):
            for name, system in self.systems.items():
                val = system.mapCoordinates
                rc = QtCore.QRectF(val["x"],
                                   val["y"],
                                   val["width"],
                                   val["height"])
                if rc.contains(pos):
                    self.mapLinkClicked(QtCore.QUrl("map_link/{0}".format(name)))
                    break
        self.ui.mapView.doubleClicked = doubleClicked

    def handleDestinationActions(self, act, destination_id, jump_route=[]) -> bool:
        if hasattr(act, "eve_action"):
            player_name = act.eve_action["player_name"]
            match act.eve_action["action"]:
                case "destination":
                    evegate.esiAutopilotWaypoint(
                        player_name,
                        destination_id)
                    return True
                case "waypoint":
                    evegate.esiAutopilotWaypoint(
                        char_name=player_name,
                        system_id=destination_id,
                        clear_all=False,
                        beginning=False)
                    return True
                case "clearall":
                    for system in self.systems.values():
                        if player_name in system.getLocatedCharacters():
                            evegate.esiAutopilotWaypoint(player_name, system.systemId)
                            return True
                case "route":
                    if len(jump_route) == 0:
                        evegate.esiAutopilotWaypoint(player_name, destination_id)
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

    def updateSidePanel(self):
        inx_qTabPOIS = self.ui.qSidepannel.indexOf(self.ui.qTabPOIS)
        inx_qTabJumpbridges = self.ui.qSidepannel.indexOf(self.ui.qTabJumpbridges)
        if evegate.esiCharName() is None:
            self.ui.qSidepannel.setTabVisible(inx_qTabPOIS, False)
            self.ui.qSidepannel.setTabVisible(inx_qTabJumpbridges, False)
        else:
            self.ui.qSidepannel.setTabVisible(inx_qTabPOIS, True)
            self.ui.qSidepannel.setTabVisible(inx_qTabJumpbridges, True)

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
            cache = Cache()
            index = self.ui.tableViewPOIs.model().mapToSource(self.ui.tableViewPOIs.indexAt(pos)).row()
            item = cache.getPOIAtIndex(index)
            lps_ctx_menu = POIContextMenu()
            lps_ctx_menu.setStyleSheet(Styles().getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewPOIs.mapToGlobal(pos))
            if item and "destination_id" in item.keys():
                if self.handleDestinationActions(res, item["destination_id"]):
                    return
                elif res == lps_ctx_menu.delete:
                    cache.clearPOI(item["destination_id"])
                    self.poi_changed.emit()
                    return

        self.ui.tableViewPOIs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
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
        system_name = Cache().getFromCache("thera_source_system")
        if system_name:
            self.ui.lineEditThera.setText(system_name)
            self.ui.tableViewThera.model().sourceModel().updateData(system_name)

        def theraSystemChanged():
            system_name = self.ui.lineEditThera.text()
            Cache().putIntoCache("thera_source_system", system_name)
            self.ui.tableViewThera.model().sourceModel().updateData(system_name)

        self.ui.lineEditThera.editingFinished.connect(theraSystemChanged)
        self.ui.toolRescanThrea.clicked.connect(theraSystemChanged)

        def showTheraContextMenu(pos):
            cache = Cache()
            index = self.ui.tableViewThera.model().mapToSource(self.ui.tableViewThera.indexAt(pos)).row()
            item = self.ui.tableViewThera.model().sourceModel().thera_data[index]
            lps_ctx_menu = TheraContextMenu()
            lps_ctx_menu.setStyleSheet(Styles().getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewPOIs.mapToGlobal(pos))
            if self.handleDestinationActions(res, item["wormholeDestinationSolarSystemId"]):
                return
            elif res == lps_ctx_menu.updateData:
                self.ui.tableViewThera.model().sourceModel().updateData()
                return

        self.ui.tableViewThera.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.tableViewThera.customContextMenuRequested.connect(showTheraContextMenu)

    def _wireUpDatabaseViewsJB(self):
        model = QSqlQueryModel()

        def callOnUpdate():
            self.mapJumpGates = Cache().getJumpGates()
            if self.dotlan:
                self.dotlan.setJumpbridges(self.mapJumpGates)
            model.setQuery("SELECT (src||' » ' ||jumpbridge.dst)as 'Gate Information', datetime(modified,'unixepoch','localtime')as 'last update', ( case used when 2 then 'okay' else 'probably okay' END ) 'Paired' FROM jumpbridge")

        callOnUpdate()

        self.jbs_changed.connect(callOnUpdate)
        sort = QSortFilterProxyModel()
        sort.setSourceModel(model)
        self.ui.tableViewJBs.setModel(sort)
        self.ui.tableViewJBs.show()

        def showJBContextMenu(pos):
            cache = Cache()
            index = self.ui.tableViewJBs.model().mapToSource(self.ui.tableViewJBs.indexAt(pos)).row()
            item = cache.getJumpGatesAtIndex(index)
            lps_ctx_menu = JumpBridgeContextMenu()
            lps_ctx_menu.setStyleSheet(Styles().getStyle())
            res = lps_ctx_menu.exec_(self.ui.tableViewJBs.mapToGlobal(pos))
            if self.handleDestinationActions(res, item["id_src"]):
                return
            elif res == lps_ctx_menu.update:
                inx_selected = self.ui.tableViewJBs.selectedIndexes()
                items = dict()
                for inx in inx_selected:
                    items[inx.row()] = cache.getJumpGatesAtIndex(inx.row())
                for item in items.values():
                    evegate.getAllJumpGates(evegate.esiCharName(), item["src"], item["dst"])
                self.jbs_changed.emit()
            elif res == lps_ctx_menu.delete:
                cache.clearJumpGate(item["src"])
                self.jbs_changed.emit()
                return

        self.ui.tableViewJBs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.tableViewJBs.customContextMenuRequested.connect(showJBContextMenu)

    def _wireUpDatabaseCharacters(self):
        char_model = TableModelPlayers()

        def callOnCharsUpdate():
            char_model.setQuery('select name as Name,' \
                                '(CASE active WHEN 0 THEN "No" ELSE "Yes" END) AS Monitor,' \
                                '(CASE WHEN key is NULL THEN "" ELSE "ESI" END ) AS Registered,' \
                                '(CASE name WHEN (SELECT data FROM cache WHERE key IS "api_char_name")' \
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

        def callOnSelChanged(name):
            evegate.setEsiCharName(name)
            self.rescanIntel()
            self.players_changed.emit()

        self.ui.currentESICharacter.clear()
        self.ui.currentESICharacter.addItems(Cache().getAPICharNames())
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
                Cache().removeAPIKey(evegate.esiCharName())
                self.ui.currentESICharacter.clear()
                self.ui.currentESICharacter.addItems(Cache().getAPICharNames())

        self.ui.removeChar.clicked.connect(callOnRemoveChar)

    def _setupThreads(self):
        logging.info("Set up threads and their connections...")
        self.avatarFindThread = AvatarFindThread()
        self.avatarFindThread.avatar_update.connect(self.updateAvatarOnChatEntry)
        self.avatarFindThread.start()

        self.filewatcherThread = filewatcher.FileWatcher(self.pathToLogs)
        self.filewatcherThread.file_change.connect(self.logFileChanged)
        self.filewatcherThread.start()

        self.statisticsThread = MapStatisticsThread()
        self.statisticsThread.statistic_data_update.connect(self.updateStatisticsOnMap)
        self.statisticsThread.start()
        self.apiThread = None
        logging.info("Set up threads and their connections done.")

    def _terminateThreads(self):
        logging.info("Stop the threads ...")
        try:
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

    def changeRegionFromCtxMenu(self, checked):
        selected_system = self.trayIcon.contextMenu().currentSystem
        if selected_system is None:
            return
        self.changeRegionBySystemID(selected_system.systemId)

    def focusMapOnSystem(self, system_id):
        """sets the system defined by the id to the focus of the map
        """
        if system_id is None:
            return
        if system_id in self.systemsById:
            selected_system = self.systemsById[system_id]
            view_center = self.ui.mapView.size() / 2
            pt_system = QPointF(selected_system.mapCoordinates["center_x"]
                                * self.ui.mapView.zoom-view_center.width(),
                                selected_system.mapCoordinates["center_y"]
                                * self.ui.mapView.zoom-view_center.height())
            self.ui.mapView.setScrollPosition(pt_system)

    def changeRegionByName(self, selected_region_name, system_id=None):
        Cache().putIntoCache("region_name", selected_region_name)
        self.setupMap()
        self.rescanIntel()
        if system_id is not None:
            self.focusMapOnSystem(system_id)
        else:
            view_center = self.ui.mapView.size() / 2
            pt_system = QPointF(1027.0/2.0
                                * self.ui.mapView.zoom - view_center.width(),
                                768.0/2.0
                                * self.ui.mapView.zoom - view_center.height())
            self.ui.mapView.setScrollPosition(pt_system)

    def changeRegionBySystemID(self, system_id):
        """ change to the region of the system with the given id, the intel will be rescanned
            and the cache region_name will be updated
        """
        if system_id is None:
            return
        self.changeRegionByName(Universe.regionNameFromSystemID(system_id), system_id)

    def prepareContextMenu(self):
        # Menus - only once
        region_name = Cache().getFromCache("region_name")
        logging.info("Initializing contextual menus")

        # Add a contextual menu to the mapView
        def mapContextMenuEvent(event):
            self.trayIcon.contextMenu().updateMenu(None)
            self.trayIcon.contextMenu().exec_(self.mapToGlobal(QPoint(event.x(), event.y())))

        self.ui.mapView.contextMenuEvent = mapContextMenuEvent
        self.ui.mapView.contextMenu = self.trayIcon.contextMenu()

        # Also set up our app menus
        if not region_name:
            self.ui.providenceCatchRegionAction.setChecked(True)
        elif region_name.startswith("Providencecatch"):
            self.ui.providenceCatchRegionAction.setChecked(True)
        elif region_name.startswith("Catch"):
            self.ui.catchRegionAction.setChecked(True)
        elif region_name.startswith("Providence"):
            self.ui.providenceRegionAction.setChecked(True)
        elif region_name.startswith("Wicked"):
            self.ui.wickedcreekScaldingpassRegionAction.setChecked(True)
        elif region_name.startswith("Tack"):
            self.ui.wickedcreekScaldingpassRegionAction.setChecked(True)
        elif region_name.startswith("Querious"):
            self.ui.queriousRegionAction.setChecked(True)
        else:
            self.ui.chooseRegionAction.setChecked(False)

        def openDotlan(checked):
            system = self.trayIcon.contextMenu().currentSystem
            if system:
                QDesktopServices.openUrl("https://evemaps.dotlan.net/system/{}".format(system.name))

        self.trayIcon.contextMenu().openDotlan.triggered.connect(openDotlan)

        def openZKillboard(checked):
            system = self.trayIcon.contextMenu().currentSystem
            if system:
                QDesktopServices.openUrl(
                    "https://zkillboard.com/system/{}".format(system.systemId))

        self.trayIcon.contextMenu().openZKillboard.triggered.connect(openZKillboard)

        def setDestination():
            name = evegate.esiCharName()
            system = self.trayIcon.contextMenu().currentSystem
            if system and name:
                evegate.esiAutopilotWaypoint(name, system.systemId)
        self.trayIcon.contextMenu().setDestination.triggered.connect(setDestination)

        self.trayIcon.contextMenu().hasJumpGate = lambda name: Cache().hasJumpGate(name)

        def clearJumpGate():
            Cache().clearJumpGate(self.trayIcon.contextMenu().currentSystem.name)
            self.jbs_changed.emit()

        self.trayIcon.contextMenu().clearJumpGate.triggered.connect(clearJumpGate)

        def addWaypoint(checked):
            name = evegate.esiCharName()
            system = self.trayIcon.contextMenu().currentSystem
            if name and system:
                evegate.esiAutopilotWaypoint(name, system, False, False)
        self.trayIcon.contextMenu().addWaypoint.triggered.connect(addWaypoint)

        def avoidSystem(checked):
            return
        self.trayIcon.contextMenu().avoidSystem.triggered.connect(avoidSystem)

        def clearAll(checked):
            char_name = evegate.esiCharName()
            for system in self.systems.values():
                if char_name in system.getLocatedCharacters():
                    evegate.esiAutopilotWaypoint(char_name, system.systemId)
                    return
            return
        self.trayIcon.contextMenu().clearAll.triggered.connect(clearAll)

        self.trayIcon.contextMenu().changeRegion.triggered.connect(self.changeRegionFromCtxMenu)

    def setupMap(self):
        logging.debug("setupMap started...")
        cache = Cache()
        region_name = cache.getFromCache("region_name")

        if not region_name:
            region_name = "Providence"

        svg = None
        try:
            res_file_name = os.path.join("vi", "ui", "res", "mapdata", "{0}.svg".format(region_name))
            if resourcePathExists(res_file_name):
                with open(resourcePath(res_file_name))as svgFile:
                    svg = svgFile.read()
                    logging.info("Using local stored map file {}".format(res_file_name))
        except Exception as e:
            logging.error(e)
            pass

        try:
            self.dotlan = dotlan.Map(
                region=region_name,
                svgFile=svg,
                setJumpMapsVisible=self.ui.jumpbridgesButton.isChecked(),
                setSatisticsVisible=self.ui.statisticsButton.isChecked(),
                setSystemStatistic=self.mapStatisticCache,
                setCampaignsSystems=self.mapCampaigns,
                setIncursionSystems=self.mapIncursions,
                setPlayerSovereignty=self.mapSovereignty,
                setJumpBridges=self.mapJumpGates)
            logging.info("Using dotlan map {}".format(region_name))
        except dotlan.DotlanException as e:
            logging.critical(e)
            QMessageBox.critical(self, "Error getting map", str(e), QMessageBox.Close)
            sys.exit(1)

        if self.dotlan.outdatedCacheError:
            e = self.dotlan.outdatedCacheError
            diag_text = "Something went wrong getting map data. Proceeding with older cached data. " \
                        "Check for a newer version and inform the maintainer.\n\nError: {0} {1}".format(type(e), str(e))
            logging.warning(diag_text)
            QMessageBox.warning(self, "Using map from cache", diag_text, QMessageBox.Ok)

        logging.debug("Creating chat parser for the current map")

        # Update the new map view, then clear old statistics from the map and request new
        logging.debug("Updating the map")
        self.updateMapView()
        self.setInitialMapPositionForRegion(region_name)
        self.mapTimer.start(MAP_UPDATE_INTERVAL_MSEC)
        # Allow the file watcher to run now that all else is set up
        logging.debug("setupMap succeeded.")

    def rescanIntel(self):
        with FileWatcher.FILE_LOCK:
            try:
                logging.info("Intel ReScan using files from watcher.")
                self.clearIntelChat()
                now = datetime.datetime.now()
                for file_path in self.filewatcherThread.files:
                    if file_path.endswith(".txt"):
                        path, file = os.path.split(file_path)
                        room_name = file[:-31]
                        modify_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                        delta = now - modify_time
                        if (delta.total_seconds() < 60 * self.chatparser.intelTime) and (delta.total_seconds() > 0):
                            if room_name in self.room_names:
                                logging.info("Reading log {}".format(room_name))
                                self.logFileChanged(file_path, rescan=True)

                logging.info("Intel ReScan done")
                self.statisticsThread.requestLocations()
                self.updateMapView()
            except Exception as e:
                logging.error(e)
            self.filewatcherThread.paused = False

    def _startStatisticTimer(self):
        self.statisticTimer = QTimer(self)
        self.statisticTimer.timeout.connect(self.statisticsThread.requestStatistics)
        self.statisticsThread.requestLocations()
        self.statisticsThread.requestStatistics()
        self.statisticsThread.requestSovereignty()
        self.statisticTimer.start(30*1000)

    def closeEvent(self, event):
        """
            Persisting things to the cache before closing the window
        """
        self.ui
        # Program state to cache (to read it on next startup)
        settings = ((None, "restoreGeometry", str(self.saveGeometry()), True),
                    (None, "restoreState", str(self.saveState()), True),
                    ("ui.splitter", "restoreGeometry", str(self.ui.splitter.saveGeometry()), True),
                    ("ui.splitter", "restoreState", str(self.ui.splitter.saveState()), True),
                    ("ui.mapView", "setZoomFactor", self.ui.mapView.zoomFactor()),
                    ("ui.qSidepannel", "restoreGeometry", str(self.ui.qSidepannel.saveGeometry()), True),
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
                    (None, "showStatistic", self.ui.statisticsButton.isChecked()))

        Cache().putIntoCache("version", str(vi.version.VERSION), 60 * 60 * 24 * 30)
        Cache().putIntoCache("settings", str(settings), 60 * 60 * 24 * 30)
        self._terminateThreads()
        self.trayIcon.hide()
        event.accept()
        QtCore.QCoreApplication.quit()

    def changeChatVisibility(self, value=None):
        if value is None:
            value = self.ui.showChatAction.isChecked()
        self.ui.showChatAction.setChecked(value)
        self.ui.chatbox.setVisible(value)

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

    def changeIntelTime(self):
        action = self.intelTimeGroup.checkedAction()
        self.intelTimeGroup.intelTime = action.intelTime
        self.chatparser.intelTime = action.intelTime
        self.ui.timeInfo.setText("All Intel( past{} minutes)".format(self.chatparser.intelTime))
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
        Cache().putIntoCache("theme", action.theme, 60 * 60 * 24 * 365)
        self.prepareContextMenu()

    def changeSound(self, value=None, disable=False):
        if disable:
            self.ui.activateSoundAction.setChecked(False)
            self.ui.activateSoundAction.setEnabled(False)
            self.ui.useSpokenNotificationsAction(False)
            self.ui.soundSetupAction.setEnabled(False)
            QMessageBox.warning(
                None, "Sound disabled",
                "The lib 'pyglet' which is used to play sounds cannot be found, ""so the soundsystem is disabled.\n" \
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
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowStaysOnTopHint))
        if do_show:
            self.show()

    def changeFrameless(self, value=None):
        if value is None:
            value = not self.ui.frameButton.isVisible()
        do_show = self.isVisible()
        if do_show:
            self.hide()
        if value:
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            self.changeAlwaysOnTop(True)
        else:
            self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.FramelessWindowHint))
        self.ui.menubar.setVisible(not value)
        self.ui.frameButton.setVisible(value)
        self.ui.framelessWindowAction.setChecked(value)

        for cm in TrayContextMenu.instances:
            cm.framelessCheck.setChecked(value)

        if do_show:
            self.show()

    def clearCache(self):
        used_cache = Cache()
        used_cache.clearOutdatedPlayerNames()
        used_cache.clearOutdatedCache()
        used_cache.clearOutdatedImages(3)
        used_cache.clearOutdatedJumpGates()

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
        self.alarmDistance = distance
        for cm in TrayContextMenu.instances:
            for action in cm.distanceGroup.actions():
                if action.alarmDistance == distance:
                    action.setChecked(True)
        self.trayIcon.alarmDistance = distance

    def changeJumpbridgesVisibility(self, val):
        self.dotlan.changeJumpbridgesVisibility(val)
        self.updateMapView()

    def changeStatisticsVisibility(self, val):
        self.dotlan.changeStatisticsVisibility(val)
        self.updateMapView()
        if val:
            self.statisticsThread.requestStatistics()

    def clipboardChanged(self, mode=0):
        """ the content of the clip board is used to set jump bridge and poi
        """
        content = str(self.clipboard.text())
        if content != self.oldClipboardContent:
            cache = Cache()
            content = str(self.clipboard.text())
            cb_type, cb_data = evaluateClipboardData(content)
            if cb_type == "poi":
                if cache.putPOI(cb_data):
                    self.poi_changed.emit()
            elif cb_type == "jumpbridge":
                if cache.putJumpGate(
                        src=cb_data["src"],
                        dst=cb_data["dst"],
                        src_id=cb_data["id_src"],
                        dst_id=cb_data["id_dst"],
                        json_src=cb_data["json_src"],
                        json_dst=cb_data["json_dst"]):
                    self.jbs_changed.emit()

    def mapLinkClicked(self, url: QtCore.QUrl):
        system_name = str(url.path().split("/")[-1])
        if system_name in self.systems:
            system = self.systems[system_name]
            sc = SystemChat(self, SystemChat.SYSTEM, system, self.chatEntries, self.knownPlayerNames)
            self.chat_message_added.connect(sc.addChatEntry)
            self.avatar_loaded.connect(sc.newAvatarAvailable)
            sc.location_set.connect(self.setLocation)
            sc.repaint_needed.connect(self.updateMapView)
            sc.show()

    def markSystemOnMap(self, system_name: str):
        if system_name in self.systems.keys():
            curr_sys = self.systems[str(system_name)]
            curr_sys.mark()
            self.updateMapView()
            self.focusMapOnSystem(curr_sys.systemId)
        else:
            self.changeRegionBySystemID(Universe.systemIdByName(system_name))

    def setLocation(self, char_name, system_name: str, change_region: bool = False):
        """
        Change the location of the char to the given system inside the current map, if required the region may be changed.

        Args:
            char_name: name of the character
            system_name: system name
            change_region: allow change of the region

        Returns:

        """
        for system in self.systems.values():
            system.removeLocatedCharacter(char_name)

        # if evegate.esiCheckCharacterToken(char_name) and not evegate.esiCharactersOnline(char_name):
        #    logging.error("Invalid locale change for character with name '{}', character is offline.".format(char_name))
        #    return
        logging.info("The location of character '{}' changed to system '{}'".format(char_name, system_name))
        self.ui.lineEditThera.setText(system_name)
        if system_name not in self.systems:
            if change_region:   # and char_name in self.monitoredPlayerNames:
                try:
                    system_id = Universe.systemIdByName(system_name)
                    selected_region_name = Universe.regionNameFromSystemID(system_id)
                    selected_region_name = dotlan.convertRegionName(selected_region_name)
                    concurrent_region_name = Cache().getFromCache("region_name")
                    if selected_region_name != concurrent_region_name:
                        self.changeRegionByName(selected_region_name, system_id)
                except Exception as e:
                    logging.error(e)
                    pass

        if not system_name == "?" and system_name in self.systems:
            self.systems[system_name].addLocatedCharacter(char_name)
            if evegate.esiCheckCharacterToken(char_name):
                self.focusMapOnSystem(self.systems[str(system_name)].systemId)

        self.updateMapView()

    def updateMapView(self):
        try:
            if self.currContent != self.dotlan.svg:
                self.mapTimer.stop()
                if self.ui.mapView.setContent(QByteArray(self.dotlan.svg.encode('utf-8'))):
                    self.currContent = self.dotlan.svg
                self.mapTimer.start(MAP_UPDATE_INTERVAL_MSEC)
        except Exception as e:
            logging.error("Error updateMapView failed: {0}".format(str(e)))
            pass

    def loadInitialMapPositions(self, new_dictionary):
        self.mapPositionsDict = new_dictionary

    def setInitialMapPositionForRegion(self, region_name):
        try:
            if not region_name:
                region_name = Cache().getFromCache("region_name")
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

    def showJumpbridgeChooser(self):
        url = Cache().getFromCache("jumpbridge_url")
        chooser = JumpbridgeChooser(self, url)
        chooser.set_jumpbridge_url.connect(self.updateJumpbridgesFromFile)
        chooser.show()

    @staticmethod
    def setSoundVolume(value):
        SoundManager().setSoundVolume(value)

    def showStatistic(self, value):
        self.ui.statisticsButton.setChecked(value)

    def showJumpbridge(self, value):
        self.ui.jumpbridgesButton.setChecked(value)

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
            cache = Cache()
            if url != "":
                if url.startswith("http://") or url.startswith("https://"):
                    resp = requests.get(url)
                    for line in resp.iter_lines(decode_unicode=True):
                        parts = line.strip().split()
                        if len(parts) > 2:
                            data.append(parts)
                elif os.path.exists(url):
                    content = []
                    with open(url, 'r') as f:
                        content = f.readlines()
                    for line in content:
                        parts = line.strip().split()
                        # src <-> dst system_id jump_bridge_id
                        if len(parts) > 2:
                            data.append(parts)
                for parts in data:
                    cache.putJumpGate(src=parts[0], dst=parts[2])
                self.jbs_changed.emit()
            Cache().putIntoCache("jumpbridge_url", url)

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
        self.ui.chooseRegionAction.setChecked(False)
        if action:
            action.setChecked(True)
            selected_region_name = str(action.property("regionName"))
            selected_region_name = dotlan.convertRegionName(selected_region_name)
            self.changeRegionByName(selected_region_name)

    def showRegionChooser(self):
        def handleRegionChosen(region_name):
            self.handleRegionMenuItemSelected(None)
            self.ui.chooseRegionAction.setChecked(False)
            self.changeRegionByName(region_name)

        self.ui.chooseRegionAction.setChecked(False)
        chooser = RegionChooser(self)
        chooser.new_region_chosen.connect(handleRegionChosen)
        chooser.show()

    def addMessageToIntelChat(self, message):
        scroll_to_bottom = False
        if self.ui.chatListWidget.verticalScrollBar().value() == self.ui.chatListWidget.verticalScrollBar().maximum():
            scroll_to_bottom = True

        if self.ui.useSpokenNotificationsAction.isChecked():
            SoundManager().playSound(
                name="alarm_1",
                abbreviatedMessage="Massage from {},  {}, The status is now {}".format(
                    message.user,
                    message.plainText,
                    message.status))

        chat_entry_widget = ChatEntryWidget(message)
        list_widget_item = QtWidgets.QListWidgetItem(self.ui.chatListWidget)
        list_widget_item.setSizeHint(chat_entry_widget.sizeHint())
        self.ui.chatListWidget.addItem(list_widget_item)
        self.ui.chatListWidget.setItemWidget(list_widget_item, chat_entry_widget)
        self.avatarFindThread.addChatEntry(chat_entry_widget)
        self.chatEntries.append(chat_entry_widget)
        chat_entry_widget.mark_system.connect(self.markSystemOnMap)
        self.chat_message_added.emit(chat_entry_widget, message.timestamp)
        self.pruneMessages()
        if scroll_to_bottom:
            self.ui.chatListWidget.scrollToBottom()

    def clearIntelChat(self):
        logging.info("Clearing Intel")
        # self.setupMap()
        try:
            while self.ui.chatListWidget.count() > 0:
                item = self.ui.chatListWidget.item(0)
                entry = self.ui.chatListWidget.itemWidget(item)
                self.chatEntries.remove(entry)
                self.ui.chatListWidget.takeItem(0)
        except Exception as e:
            logging.error(e)

    def pruneMessages(self):
        try:
            now = time.mktime(evegate.currentEveTime().timetuple())
            now_to = time.time()
            for row in range(self.ui.chatListWidget.count()):
                chat_list_widget_item = self.ui.chatListWidget.item(0)
                chat_entry_widget = self.ui.chatListWidget.itemWidget(chat_list_widget_item)
                message = chat_entry_widget.message
                if now - time.mktime(message.timestamp.timetuple()) > (60 * self.chatparser.intelTime):
                    self.chatEntries.remove(chat_entry_widget)
                    self.ui.chatListWidget.takeItem(0)
                else:
                    break
        except Exception as e:
            logging.error(e)

    def changedRoomNames(self, names):
        Cache().putIntoCache("room_names", u",".join(names), 60 * 60 * 24 * 365 * 5)
        self.chatparser.rooms = names

    def showInfo(self):
        info_dialog = QtWidgets.QDialog(self)
        info_dialog.ui = Ui_Info()
        info_dialog.ui.setupUi(info_dialog)
        info_dialog.ui.versionLabel.setText(u"Version: {0}".format(vi.version.VERSION))
        # info_dialog.ui.logoLabel.setPixmap(QtGui.QPixmap(resourcePath(os.path.join("vi", "ui", "res", "denci.png"))))
        info_dialog.ui.closeButton.clicked.connect(info_dialog.accept)
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
            lambda: SoundManager().playSound(name="alarm", abbreviatedMessage="Testing the playback sound system!"))
        dialog.ui.palyAlarm_1.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_1", abbreviatedMessage="Alarm distance 1"))
        dialog.ui.palyAlarm_2.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_2", abbreviatedMessage="Alarm distance 2"))
        dialog.ui.palyAlarm_3.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_3", abbreviatedMessage="Alarm distance 3"))
        dialog.ui.palyAlarm_4.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_4", abbreviatedMessage="Alarm distance 4"))
        dialog.ui.palyAlarm_5.clicked.connect(
            lambda: SoundManager().playSound(name="alarm_5", abbreviatedMessage="Alarm distance 5"))
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
            self.avatarFindThread.addChatEntry(entry, clearCache=True)

    def updateStatisticsOnMap(self, data):
        if data["result"] == "ok":
            if "statistics" in data:
                self.mapStatisticCache = data["statistics"]
                if self.dotlan:
                    self.dotlan.addSystemStatistics(data['statistics'])

            if "sovereignty" in data:
                self.mapSovereignty = data['sovereignty']
                if self.dotlan:
                    self.dotlan.setSystemSovereignty(data['sovereignty'])

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

            logging.debug("Map statistic update  succeeded.")
        elif data["result"] == "error":
            text = data["text"]
            self.trayIcon.showMessage("Loading statistics failed", text, 3)
            logging.error("updateStatisticsOnMap, error: %s" % text)

    def zoomMapIn(self):
        self.ui.mapView.zoomIn()

    def zoomMapOut(self):
        self.ui.mapView.zoomOut()

    def logFileChanged(self, path, rescan=False):
        locale_to_set = dict()
        messages = self.chatparser.fileModified(path, self.systems, rescan)
        for message in messages:
            # If players location has changed
            if message.status == states.LOCATION:
                locale_to_set[message.user] = message.systems
            elif message.canProcess():
                self.addMessageToIntelChat(message)
                """
                 For each system that was mentioned in the message, check for alarm distance to the current system
                 and alarm if within alarm distance.
                """
                systems_on_map = self.systems
                if message.systems:
                    for system in message.systems:
                        system_name = system.name
                        if system_name in systems_on_map.keys():
                            systems_on_map[system_name].setStatus(message.status, message.timestamp)
                        is_alarm = message.status == states.ALARM
                        if is_alarm and message.user not in self.knownPlayerNames:
                            alarm_distance = self.alarmDistance if is_alarm else 0
                            for nSystem, data in system.getNeighbours(alarm_distance).items():
                                if "distance" not in data:
                                    continue
                                chars = nSystem.getLocatedCharacters()
                                if len(chars) > 0:
                                    if len(self.monitoredPlayerNames.intersection(set(chars))) > 0 and message.user not in chars:
                                        self.trayIcon.showNotification(
                                            message,
                                            system.name,
                                            ", ".join(chars),
                                            data["distance"])

        for name, systems in locale_to_set.items():
            self._updateKnownPlayerAndMenu(name)
            for sys_name in systems:
                self.setLocation(name, sys_name, self.autoChangeRegion)

        if not rescan:
            self.updateMapView()

    def systemUnderMouse(self, pos: QPoint) -> Optional[dotlan.System]:
        """returns the name of the system under the mouse pointer
        """
        for name, system in self.systems.items():
            val = system.mapCoordinates
            rc = QtCore.QRectF(val["x"], val["y"], val["width"], val["height"])
            if rc.contains(pos):
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
            lambda: self.changeRegionBySystemID(selected_system.systemId))
        map_ctx_menu.alarm_distance.connect(self.changeAlarmDistance)
        map_ctx_menu.setStyleSheet(Styles().getStyle())

        if selected_system:
            concurrent_region_name = Cache().getFromCache("region_name")
            selected_region_name = Universe.regionNameFromSystemID(selected_system.systemId)
            if dotlan.convertRegionName(selected_region_name) == concurrent_region_name:
                selected_region_name = None
            map_ctx_menu.updateMenu(sys_name=selected_system,
                                    rgn_name=selected_region_name,
                                    alarm_distance=self.alarmDistance)
        else:
            map_ctx_menu.updateMenu(alarm_distance=self.alarmDistance)
        res = map_ctx_menu.exec_(self.mapToGlobal(QPoint(event.x(), event.y())))
        if selected_system:
            if self.handleDestinationActions(res, selected_system.systemId):
                return

