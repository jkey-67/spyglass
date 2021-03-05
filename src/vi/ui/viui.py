###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import os
import datetime
import sys
import time
import requests
import webbrowser
import threading

import vi.version

import logging
from PyQt5.QtGui import *
from PyQt5 import QtGui, uic, QtCore, QtWidgets

from PyQt5.QtCore import QPoint,QPointF, QByteArray, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMessageBox, QStyleOption, QStyle, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView,QWebEnginePage

from vi import amazon_s3, evegate
from vi import dotlan, filewatcher
from vi import states
from vi.cache.cache import Cache
from vi.resources import resourcePath
from vi.soundmanager import SoundManager
from vi.threads import AvatarFindThread, KOSCheckerThread, MapStatisticsThread, VoiceOverThread
from vi.ui.systemtray import TrayContextMenu
from vi.ui.styles import Styles
from vi.chatparser import ChatParser
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QActionGroup
from PyQt5.QtWidgets import QMessageBox

# Timer intervals
MESSAGE_EXPIRY_SECS = 20 * 60
MAP_UPDATE_INTERVAL_MSECS = 4 * 1000
CLIPBOARD_CHECK_INTERVAL_MSECS = 4 * 1000


class MainWindow(QtWidgets.QMainWindow):

    chat_message_added = pyqtSignal(object, object)
    avatar_loaded = pyqtSignal(object, object)
    def __init__(self, pathToLogs, trayIcon, backGroundColor):

        QtWidgets.QMainWindow.__init__(self)
        self.cache = Cache()

        if backGroundColor:
            self.setStyleSheet("QWidget { background-color: %s; }" % backGroundColor)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "MainWindow.ui")), self)
        self.setWindowTitle(
            "Spyglass " + vi.version.VERSION + "{dev}".format(dev="-SNAPSHOT" if vi.version.SNAPSHOT else ""))
        self.taskbarIconQuiescent = QtGui.QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")))
        self.taskbarIconWorking = QtGui.QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small_green.png")))
        self.setWindowIcon(self.taskbarIconQuiescent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.pathToLogs = pathToLogs
        self.mapTimer = QtCore.QTimer(self)
        #self.mapTimer.timeout.connect(self.updateMapView)
        self.mapView.page().loadFinished.connect(self.onLoadFinished)
        self.clipboardTimer = QtCore.QTimer(self)
        self.oldClipboardContent = ""
        self.trayIcon = trayIcon
        self.trayIcon.activated.connect(self.systemTrayActivated)
        self.clipboard = QtWidgets.QApplication.clipboard()
        self.clipboard.clear(mode=self.clipboard.Clipboard)
        self.alarmDistance = 0
        self.lastStatisticsUpdate = 0
        self.chatEntries = []
        self.frameButton.setVisible(False)
        self.scanIntelForKosRequestsEnabled = True
        self.initialMapPosition = None
        self.oldSvg = None
        self.mapPositionsDict = {}
        self.ignoreCount = 1

        self.autoRescanIntelEnabled = self.cache.getFromCache("changeAutoRescanIntel")

        # Load user's toon names
        self.knownPlayerNames = self.cache.getFromCache("known_player_names")
        if self.knownPlayerNames:
            self.knownPlayerNames = set(self.knownPlayerNames.split(","))
        else:
            self.knownPlayerNames = set()
            diagText = "Spyglass scans EVE system logs and remembers your characters as they change systems.\n\nSome features (clipboard KOS checking, alarms, etc.) may not work until your character(s) have been registered. Change systems, with each character you want to monitor, while Spyglass is running to remedy this."
            QMessageBox.warning(None, "Known Characters not Found", diagText, QMessageBox.Ok)

        # Set up user's intel rooms
        roomnames = self.cache.getFromCache("room_names")
        if roomnames:
            roomnames = roomnames.split(",")
        else:
            roomnames = (u"TheCitadel", u"North Provi Intel", u"4THINTEL")
            self.cache.putIntoCache("room_names", u",".join(roomnames), 60 * 60 * 24 * 365 * 5)
        self.roomnames = roomnames

        # Disable the sound UI if sound is not available
        if not SoundManager().soundAvailable:
            self.changeSound(disable=True)
        else:
            self.changeSound()

        # Set up Transparency menu - fill in opacity values and make connections
        self.opacityGroup = QActionGroup(self.menu)
        for i in (100, 80, 60, 40, 20):
            action = QAction("Opacity {0}%".format(i), None, checkable=True)
            if i == 100:
                action.setChecked(True)
            action.opacity = i / 100.0
            action.triggered.connect(self.changeOpacity)
            self.opacityGroup.addAction(action)
            self.menuTransparency.addAction(action)

        # Set up Theme menu - fill in list of themes and add connections
        self.themeGroup = QActionGroup(self.menu)
        styles = Styles()
        for theme in styles.getStyles():
            action = QAction(theme, None, checkable=True)
            action.theme = theme
            if action.theme == "default":
                action.setChecked(True)
            logging.info("Adding theme {}".format(theme))
            action.triggered.connect(self.changeTheme)
            self.themeGroup.addAction(action)
            self.menuTheme.addAction(action)
        styles = None

        #
        # Platform specific UI resizing - we size items in the resource files to look correct on the mac,
        # then resize other platforms as needed
        #
        if sys.platform.startswith("win32") or sys.platform.startswith("cygwin"):
            font = self.statisticsButton.font()
            font.setPointSize(8)
            self.statisticsButton.setFont(font)
            self.jumpbridgesButton.setFont(font)
        elif sys.platform.startswith("linux"):
            pass

        self.wireUpUIConnections()
        self.recallCachedSettings()
        self.setupThreads()
        self.setupMap(True)

        initialTheme = self.cache.getFromCache("theme")
        if initialTheme:
            self.changeTheme(initialTheme)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

    def recallCachedSettings(self):
        try:
            self.cache.recallAndApplySettings(self, "settings")
        except Exception as e:
            logging.error(e)
            # todo: add a button to delete the cache / DB
            self.trayIcon.showMessage("Settings error",
                                      "Something went wrong loading saved state:\n {0}".format(str(e)), 1)

    def wireUpUIConnections(self):
        # Wire up general UI connections
        self.clipboard.dataChanged.connect(self.clipboardChanged)
        self.autoScanIntelAction.triggered.connect(self.changeAutoScanIntel)
        self.kosClipboardActiveAction.triggered.connect(self.changeKosCheckClipboard)
        self.zoomInButton.clicked.connect(self.zoomMapIn)
        self.zoomOutButton.clicked.connect(self.zoomMapOut)
        self.statisticsButton.clicked.connect(self.changeStatisticsVisibility)
        self.jumpbridgesButton.clicked.connect(self.changeJumpbridgesVisibility)
        self.chatLargeButton.clicked.connect(self.chatLarger)
        self.chatSmallButton.clicked.connect(self.chatSmaller)
        self.infoAction.triggered.connect(self.showInfo)
        self.showChatAvatarsAction.triggered.connect(self.changeShowAvatars)
        self.alwaysOnTopAction.triggered.connect(self.changeAlwaysOnTop)
        self.chooseChatRoomsAction.triggered.connect(self.showChatroomChooser)
        self.catchRegionAction.triggered.connect(lambda: self.handleRegionMenuItemSelected(self.catchRegionAction))
        self.providenceRegionAction.triggered.connect(lambda: self.handleRegionMenuItemSelected(self.providenceRegionAction))
        self.queriousRegionAction.triggered.connect(lambda: self.handleRegionMenuItemSelected(self.queriousRegionAction))
        self.providenceCatchRegionAction.triggered.connect(lambda: self.handleRegionMenuItemSelected(self.providenceCatchRegionAction))
        self.providenceCatchCompactRegionAction.triggered.connect(lambda: self.handleRegionMenuItemSelected(self.providenceCatchCompactRegionAction))
        self.chooseRegionAction.triggered.connect(self.showRegionChooser)
        self.showChatAction.triggered.connect(self.changeChatVisibility)
        self.soundSetupAction.triggered.connect(self.showSoundSetup)
        self.activateSoundAction.triggered.connect(self.changeSound)
        self.useSpokenNotificationsAction.triggered.connect(self.changeUseSpokenNotifications)
        self.trayIcon.alarm_distance.connect(self.changeAlarmDistance)
        self.framelessWindowAction.triggered.connect(self.changeFrameless)
        self.trayIcon.change_frameless.connect(self.changeFrameless)
        self.frameButton.clicked.connect(self.changeFrameless)
        self.quitAction.triggered.connect(self.close)
        self.trayIcon.quit_signal.connect(self.close)
        self.jumpbridgeDataAction.triggered.connect(self.showJumbridgeChooser)
        self.rescanNowAction.triggered.connect(self.rescanIntel)
        self.clearIntelAction.triggered.connect(self.clearIntelChat)
        self.autoRescanAction.triggered.connect(self.changeAutoRescanIntel)
        self.mapView.page().scrollPositionChanged.connect(self.mapPositionChanged)

    def setupThreads(self):
        # Set up threads and their connections
        self.avatarFindThread = AvatarFindThread()
        self.avatarFindThread.avatar_update.connect(self.updateAvatarOnChatEntry)
        self.avatarFindThread.start()

        self.kosRequestThread = KOSCheckerThread()
        self.kosRequestThread.kos_result.connect(self.showKosResult)
        self.kosRequestThread.start()

        self.filewatcherThread = filewatcher.FileWatcher(self.pathToLogs)
        self.filewatcherThread.file_change.connect(self.logFileChanged)
        self.filewatcherThread.start()

        self.versionCheckThread = amazon_s3.NotifyNewVersionThread()
        self.versionCheckThread.newer_version.connect(self.notifyNewerVersion)
        self.versionCheckThread.start()

        self.statisticsThread = MapStatisticsThread()
        self.statisticsThread.statistic_data_update.connect(self.updateStatisticsOnMap)
        self.statisticsThread.start()
        # statisticsThread is blocked until first call of requestStatistics

        self.voiceThread = VoiceOverThread()
        self.voiceThread.start()

    def setupMap(self, initialize=False):
        self.mapTimer.stop()
        self.filewatcherThread.paused = True

        logging.info("Finding map file")
        regionName = self.cache.getFromCache("region_name")
        if not regionName:
            regionName = "Providence"
        svg = None
        try:
            with open(resourcePath(os.path("vi", "ui", "res", "mapdata/{0}.svg".format(regionName)))) as svgFile:
                svg = svgFile.read()
        except Exception as e:
            pass

        try:
            self.dotlan = dotlan.Map(regionName, svg)
        except dotlan.DotlanException as e:
            logging.error(e)
            QMessageBox.critical(None, "Error getting map", str(e), QMessageBox.Close)
            sys.exit(1)

        if self.dotlan.outdatedCacheError:
            e = self.dotlan.outdatedCacheError
            diagText = "Something went wrong getting map data. Proceeding with older cached data. " \
                       "Check for a newer version and inform the maintainer.\n\nError: {0} {1}".format(type(e),
                                                                                                       str(e))
            logging.warning(diagText)
            QMessageBox.warning(None, "Using map from cache", diagText, QMessageBox.Ok)

        # Load the jumpbridges
        logging.critical("Load jump bridges")
        self.setJumpbridges(self.cache.getFromCache("jumpbridge_url"))
        self.systems = self.dotlan.systems
        logging.critical("Creating chat parser")
        self.chatparser = ChatParser(self.pathToLogs, self.roomnames, self.systems)

        # Menus - only once
        if initialize:
            logging.critical("Initializing contextual menus")

            # Add a contextual menu to the mapView
            def mapContextMenuEvent(event):
                # if QApplication.activeWindow() or QApplication.focusWidget():
                self.mapView.contextMenu.exec_(self.mapToGlobal(QPoint(event.x(), event.y())))

            self.mapView.contextMenuEvent = mapContextMenuEvent
            self.mapView.contextMenu = self.trayIcon.contextMenu()

            # Clicking links
            #self.mapView.linkClicked.connect(self.mapLinkClicked)

            # Also set up our app menus
            if not regionName:
                self.providenceCatchRegionAction.setChecked(True)
            elif regionName.startswith("Providencecatch"):
                self.providenceCatchRegionAction.setChecked(True)
            elif regionName.startswith("Catch"):
                self.catchRegionAction.setChecked(True)
            elif regionName.startswith("Providence"):
                self.providenceRegionAction.setChecked(True)
            elif regionName.startswith("Querious"):
                self.queriousRegionAction.setChecked(True)
            else:
                self.chooseRegionAction.setChecked(True)
        self.jumpbridgesButton.setChecked(False)
        self.statisticsButton.setChecked(False)

        # Update the new map view, then clear old statistics from the map and request new
        logging.critical("Updating the map")
        self.updateMapView()
        self.setInitialMapPositionForRegion(regionName)
        self.mapTimer.start(MAP_UPDATE_INTERVAL_MSECS)
        # Allow the file watcher to run now that all else is set up
        self.filewatcherThread.paused = False
        logging.critical("Map setup complete")

    # def eventFilter(self, obj, event):
    #     if event.type() == QtCore.QEvent.WindowDeactivate:
    #         self.enableContextMenu(False)
    #         return True
    #     elif event.type() == QtCore.QEvent.WindowActivate:
    #         self.enableContextMenu(True)
    #         return True
    #     return False

    def rescanIntel(self):
        logging.info("Intel ReScan begun")
        self.clearIntelChat()

        now = datetime.datetime.now()
        for file in os.listdir(self.pathToLogs):
            if file.endswith(".txt"):
                filePath = self.pathToLogs + str(os.sep) + file
                roomname = file[:-20]

                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filePath))
                delta = (now - mtime)

                if delta.total_seconds() < (60 * 20) and delta.total_seconds() > 0:
                    if roomname in self.roomnames:
                        logging.info("Reading log {}".format(roomname))
                        self.logFileChanged(filePath, True)

    def startClipboardTimer(self):
        """
            Start a timer to check the keyboard for changes and kos check them,
            first initializing the content so we dont kos check from random content
        """
        self.oldClipboardContent = tuple(str(self.clipboard.text()))
        self.clipboardTimer.timeout.connect(self.clipboardChanged)
        self.clipboardTimer.start(CLIPBOARD_CHECK_INTERVAL_MSECS)

    def stopClipboardTimer(self):
        if self.clipboardTimer:
            self.disconnect()
            self.clipboardTimer.stop()

    def closeEvent(self, event):
        """
            Persisting things to the cache before closing the window
        """
        # Known playernames
        if self.knownPlayerNames:
            value = ",".join(self.knownPlayerNames)
            self.cache.putIntoCache("known_player_names", value, 60 * 60 * 24 * 30)

        # Program state to cache (to read it on next startup)
        settings = ((None, "restoreGeometry", str(self.saveGeometry())), (None, "restoreState", str(self.saveState())),
                    ("splitter", "restoreGeometry", str(self.splitter.saveGeometry())),
                    ("splitter", "restoreState", str(self.splitter.saveState())),
                    ("mapView", "setZoomFactor", self.mapView.zoomFactor()),
                    (None, "changeChatFontSize", ChatEntryWidget.TEXT_SIZE),
                    (None, "changeOpacity", self.opacityGroup.checkedAction().opacity),
                    (None, "changeAlwaysOnTop", self.alwaysOnTopAction.isChecked()),
                    (None, "changeShowAvatars", self.showChatAvatarsAction.isChecked()),
                    (None, "changeAlarmDistance", self.alarmDistance),
                    (None, "changeSound", self.activateSoundAction.isChecked()),
                    (None, "changeChatVisibility", self.showChatAction.isChecked()),
                    (None, "loadInitialMapPositions", self.mapPositionsDict),
                    (None, "setSoundVolume", SoundManager().soundVolume),
                    (None, "changeFrameless", self.framelessWindowAction.isChecked()),
                    (None, "changeUseSpokenNotifications", self.useSpokenNotificationsAction.isChecked()),
                    (None, "changeKosCheckClipboard", self.kosClipboardActiveAction.isChecked()),
                    (None, "changeAutoScanIntel", self.scanIntelForKosRequestsEnabled),
                    (None, "changeAutoRescanIntel", self.autoRescanIntelEnabled))
        self.cache.putIntoCache("settings", str(settings), 60 * 60 * 24 * 30)

        # Stop the threads
        try:
            SoundManager().quit()
            self.avatarFindThread.quit()
            self.avatarFindThread.wait()
            self.filewatcherThread.quit()
            self.filewatcherThread.wait()
            self.kosRequestThread.quit()
            self.kosRequestThread.wait()
            self.versionCheckThread.quit()
            self.versionCheckThread.wait()
            self.statisticsThread.quit()
            self.statisticsThread.wait()
            self.voiceThread.join()
        except Exception:
            pass
        self.trayIcon.hide()
        event.accept()

    def notifyNewerVersion(self, newestVersion):
        self.trayIcon.showMessage("Newer Version", ("An update is available for Spyglass.\n www.crypta.tech"), 1)

    def changeChatVisibility(self, newValue=None):
        if newValue is None:
            newValue = self.showChatAction.isChecked()
        self.showChatAction.setChecked(newValue)
        self.chatbox.setVisible(newValue)

    def changeKosCheckClipboard(self, newValue=None):
        if newValue is None:
            newValue = self.kosClipboardActiveAction.isChecked()
        self.kosClipboardActiveAction.setChecked(newValue)
        if newValue:
            self.startClipboardTimer()
        else:
            self.stopClipboardTimer()

    def changeAutoScanIntel(self, newValue=None):
        if newValue is None:
            newValue = self.autoScanIntelAction.isChecked()
        self.autoScanIntelAction.setChecked(newValue)
        self.autoRescanIntelEnabled = newValue

    def changeAutoRescanIntel(self, newValue=None):
        if newValue is None:
            newValue = self.autoRescanAction.isChecked()
        self.autoRescanAction.setChecked(newValue)
        self.autoRescanIntelEnabled = newValue

    def changeUseSpokenNotifications(self, newValue=None):
        if SoundManager().platformSupportsSpeech():
            if newValue is None:
                newValue = self.useSpokenNotificationsAction.isChecked()
            self.useSpokenNotificationsAction.setChecked(newValue)
            SoundManager().setUseSpokenNotifications(newValue)
        else:
            self.useSpokenNotificationsAction.setChecked(False)
            self.useSpokenNotificationsAction.setEnabled(False)

    def changeOpacity(self, newValue=None):
        if newValue is not None:
            for action in self.opacityGroup.actions():
                if action.opacity == newValue:
                    action.setChecked(True)
                else:
                    action.setChecked(False)
        action = self.opacityGroup.checkedAction()
        self.setWindowOpacity(action.opacity)

    def changeTheme(self, newTheme=None):
        if newTheme is not None:
            for action in self.themeGroup.actions():
                if action.theme == newTheme:
                    action.setChecked(True)
        action = self.themeGroup.checkedAction()
        styles = Styles()
        styles.setStyle(action.theme)
        theme = styles.getStyle()
        self.setStyleSheet(theme)
        logging.critical("Setting new theme: {}".format(action.theme))
        self.cache.putIntoCache("theme", action.theme, 60 * 60 * 24 * 365)
        self.setupMap()
        self.clearIntelChat()
        if self.autoRescanIntelEnabled:
            self.rescanIntel()

    def changeSound(self, newValue=None, disable=False):
        if disable:
            self.activateSoundAction.setChecked(False)
            self.activateSoundAction.setEnabled(False)
            self.soundSetupAction.setEnabled(False)
            # self.soundButton.setEnabled(False)
            QMessageBox.warning(None, "Sound disabled",
                                "The lib 'pyglet' which is used to play sounds cannot be found, ""so the soundsystem is disabled.\nIf you want sound, please install the 'pyglet' library. This warning will not be shown again.",
                                QMessageBox.Ok)
        else:
            if newValue is None:
                newValue = self.activateSoundAction.isChecked()
            self.activateSoundAction.setChecked(newValue)
            SoundManager().soundActive = newValue

    def changeAlwaysOnTop(self, newValue=None):
        if newValue is None:
            newValue = self.alwaysOnTopAction.isChecked()
        self.hide()
        self.alwaysOnTopAction.setChecked(newValue)
        if newValue:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowStaysOnTopHint))
        self.show()

    def changeFrameless(self, newValue=None):
        if newValue is None:
            newValue = not self.frameButton.isVisible()
        self.hide()
        if newValue:
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            self.changeAlwaysOnTop(True)
        else:
            self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.FramelessWindowHint))
        self.menubar.setVisible(not newValue)
        self.frameButton.setVisible(newValue)
        self.framelessWindowAction.setChecked(newValue)

        for cm in TrayContextMenu.instances:
            cm.framelessCheck.setChecked(newValue)
        self.show()

    def changeShowAvatars(self, newValue=None):
        if newValue is None:
            newValue = self.showChatAvatarsAction.isChecked()
        self.showChatAvatarsAction.setChecked(newValue)
        ChatEntryWidget.SHOW_AVATAR = newValue
        for entry in self.chatEntries:
            entry.avatarLabel.setVisible(newValue)

    def changeChatFontSize(self, newSize):
        if newSize:
            for entry in self.chatEntries:
                entry.changeFontSize(newSize)
            ChatEntryWidget.TEXT_SIZE = newSize

    def chatSmaller(self):
        newSize = ChatEntryWidget.TEXT_SIZE - 1
        self.changeChatFontSize(newSize)

    def chatLarger(self):
        newSize = ChatEntryWidget.TEXT_SIZE + 1
        self.changeChatFontSize(newSize)

    def changeAlarmDistance(self, distance):
        self.alarmDistance = distance
        for cm in TrayContextMenu.instances:
            for action in cm.distanceGroup.actions():
                if action.alarmDistance == distance:
                    action.setChecked(True)
        self.trayIcon.alarmDistance = distance

    def changeJumpbridgesVisibility(self):
        newValue = self.dotlan.changeJumpbridgesVisibility()
        self.jumpbridgesButton.setChecked(newValue)
        self.updateMapView()

    def changeStatisticsVisibility(self):
        newValue = self.dotlan.changeStatisticsVisibility()
        self.statisticsButton.setChecked(newValue)
        self.updateMapView()
        if newValue:
            self.statisticsThread.requestStatistics()

    def clipboardChanged(self, mode=0):
        if not (mode == 0 and self.kosClipboardActiveAction.isChecked() and self.clipboard.mimeData().hasText()):
            return
        content = str(self.clipboard.text())
        contentTuple = tuple(content)
        # Limit redundant kos checks
        if contentTuple != self.oldClipboardContent:
            parts = tuple(content.split("\n"))
            knownPlayers = self.knownPlayerNames
            for part in parts:
                # Make sure user is in the content (this is a check of the local system in Eve).
                # also, special case for when you have no knonwnPlayers (initial use)
                if not knownPlayers or part in knownPlayers:
                    self.trayIcon.setIcon(self.taskbarIconWorking)
                    self.kosRequestThread.addRequest(parts, "clipboard", True)
                    break
            self.oldClipboardContent = contentTuple

    def mapLinkClicked(self, url):
        systemName = str(url.path().split("/")[-1]).upper()
        system = self.systems[str(systemName)]
        sc = SystemChat(self, SystemChat.SYSTEM, system, self.chatEntries, self.knownPlayerNames)
        self.chat_message_added.connect(sc.addChatEntry)
        self.avatar_loaded.connect(sc.newAvatarAvailable)
        sc.location_set.connect(self.setLocation)
        sc.show()

    def markSystemOnMap(self, systemname, timeA=time.time()):
        self.systems[str(systemname)].mark(timeA)
        self.updateMapView()

    def setLocation(self, char, newSystem):
        for system in self.systems.values():
            system.removeLocatedCharacter(char)
        if not newSystem == "?" and newSystem in self.systems:
            self.systems[newSystem].addLocatedCharacter(char)
            self.setMapContent(self.dotlan.svg)

    def onLoadFinished(self, fin):
        self.mapView.setScrollPosition(self.initialMapPosition)
        self.initialMapPosition = None
        return

    def setMapContent(self, content):
        if (( self.oldSvg != None) and (  self.oldSvg == content)):
            return
        self.ignoreCount = 1
        self.mapView.setContent(QByteArray(content.encode('utf-16')), "text/html")
        self.setInitialMapPositionForRegion(None)
        # self.mapView.setScrollPosition(self.initialMapPosition)
        # Make sure we have positioned the window before we nil the initial position;
        # even though we set it, it may not take effect until the map is fully loaded
        self.oldSvg = content

    def loadInitialMapPositions(self, newDictionary):
        self.mapPositionsDict = newDictionary

    def setInitialMapPositionForRegion(self, regionName):
        try:
            if not regionName:
                regionName = self.cache.getFromCache("region_name")
            if regionName :
                xy = self.mapPositionsDict[regionName]
                self.initialMapPosition = QPointF(xy[0], xy[1])
        except Exception:
            pass

    def mapPositionChanged(self, scrollPosition):
        regionName = self.cache.getFromCache("region_name")
        if regionName and ( self.ignoreCount == 0 ):
            self.mapPositionsDict[regionName] = (scrollPosition.x(), scrollPosition.y())
            xy = self.mapPositionsDict[regionName]
            logging.critical("mapPositionChanged CPoint({0},{1})".format(xy[0], xy[1]))
        elif ( self.ignoreCount == 1 ):
            self.ignoreCount = 2
            self.setInitialMapPositionForRegion(None)
            self.mapView.setScrollPosition(self.initialMapPosition)
        else:
            self.ignoreCount = 0

    def showChatroomChooser(self):
        chooser = ChatroomsChooser(self)
        chooser.rooms_changed.connect(self.changedRoomnames)
        chooser.show()

    def showJumbridgeChooser(self):
        url = self.cache.getFromCache("jumpbridge_url")
        chooser = JumpbridgeChooser(self, url)
        chooser.set_jumpbridge_url.connect(self.setJumpbridges)
        chooser.show()

    def setSoundVolume(self, value):
        SoundManager().setSoundVolume(value)

    def setJumpbridges(self, url):
        logging.info("setJB")
        if url is None:
            url = ""
        try:
            data = []
            if url != "":
                if url.startswith("http://") or url.startswith("https://"):
                    resp = requests.get(url)
                    for line in resp.iter_lines(decode_unicode=True):
                        parts = line.strip().split()
                        if len(parts) == 3:
                            data.append(parts)
                else:
                    content = None
                    with open(url, 'r') as f:
                        content = f.readlines()

                    for line in content:
                        parts = line.strip().split()
                        if len(parts) == 3:
                            data.append(parts)
            else:
                data = amazon_s3.getJumpbridgeData(self.dotlan.region.lower())
            self.dotlan.setJumpbridges(data)
            self.cache.putIntoCache("jumpbridge_url", url, 60 * 60 * 24 * 365 * 8)
        except Exception as e:
            logging.error("Error: {0}".format(str(e)))
            QMessageBox.warning(None, "Loading jumpbridges failed!", "Error: {0}".format(str(e)), QMessageBox.Ok)

    def handleRegionMenuItemSelected(self, menuAction=None):
        self.catchRegionAction.setChecked(False)
        self.providenceRegionAction.setChecked(False)
        self.queriousRegionAction.setChecked(False)
        self.providenceCatchRegionAction.setChecked(False)
        self.providenceCatchCompactRegionAction.setChecked(False)
        self.chooseRegionAction.setChecked(False)
        if menuAction:
            menuAction.setChecked(True)
            regionName = str(menuAction.property("regionName"))
            regionName = dotlan.convertRegionName(regionName)
            Cache().putIntoCache("region_name", regionName, 60 * 60 * 24 * 365)
            self.setupMap()

    def showRegionChooser(self):
        def handleRegionChosen():
            self.handleRegionMenuItemSelected(None)
            self.chooseRegionAction.setChecked(True)
            self.setupMap()

        self.chooseRegionAction.setChecked(False)
        chooser = RegionChooser(self)
        chooser.finished.connect(handleRegionChosen)
        chooser.show()

    def addMessageToIntelChat(self, message, timeA=time.time()):
        scrollToBottom = False
        if (self.chatListWidget.verticalScrollBar().value() == self.chatListWidget.verticalScrollBar().maximum()):
            scrollToBottom = True
        chatEntryWidget = ChatEntryWidget(message)
        listWidgetItem = QtWidgets.QListWidgetItem(self.chatListWidget)
        listWidgetItem.setSizeHint(chatEntryWidget.sizeHint())
        self.chatListWidget.addItem(listWidgetItem)
        self.chatListWidget.setItemWidget(listWidgetItem, chatEntryWidget)
        self.avatarFindThread.addChatEntry(chatEntryWidget)
        self.chatEntries.append(chatEntryWidget)
        chatEntryWidget.mark_system.connect(self.markSystemOnMap)
        self.chat_message_added.emit(chatEntryWidget, timeA)
        self.pruneMessages()
        if scrollToBottom:
            self.chatListWidget.scrollToBottom()

    def clearIntelChat(self):
        logging.info("Clearing Intel")
        self.setupMap()
        try:
            for row in range(self.chatListWidget.count()):
                item = self.chatListWidget.item(0)
                entry = self.chatListWidget.itemWidget(item)
                message = entry.message
                self.chatEntries.remove(entry)
                self.chatListWidget.takeItem(0)
                for widgetInMessage in message.widgets:
                    widgetInMessage.removeItemWidget(item)
        except Exception as e:
            logging.error(e)

    def pruneMessages(self):
        try:
            now = time.mktime(evegate.currentEveTime().timetuple())
            for row in range(self.chatListWidget.count()):
                chatListWidgetItem = self.chatListWidget.item(0)
                chatEntryWidget = self.chatListWidget.itemWidget(chatListWidgetItem)
                message = chatEntryWidget.message
                if now - time.mktime(message.timestamp.timetuple()) > MESSAGE_EXPIRY_SECS:
                    self.chatEntries.remove(chatEntryWidget)
                    self.chatListWidget.takeItem(0)

                    for widgetInMessage in message.widgets:
                        widgetInMessage.removeItemWidget(chatListWidgetItem)
                else:
                    break
        except Exception as e:
            logging.error(e)

    def showKosResult(self, state, text, requestType, hasKos):
        if not self.scanIntelForKosRequestsEnabled:
            return
        try:
            if hasKos:
                SoundManager().playSound("kos", text)
            if state == "ok":
                if requestType == "xxx":  # An xxx request out of the chat
                    self.trayIcon.showMessage("Player KOS-Check", text, 1)
                elif requestType == "clipboard":  # request from clipboard-change
                    if len(text) <= 0:
                        text = "None KOS"
                    self.trayIcon.showMessage("Your KOS-Check", text, 1)
                text = text.replace("\n\n", "<br>")
                message = chatparser.chatparser.Message("Spyglass KOS-Check", text, evegate.currentEveTime(), "Spyglass",
                                                        [], states.NOT_CHANGE, text.upper(), text)
                self.addMessageToIntelChat(message)
            elif state == "error":
                self.trayIcon.showMessage("KOS Failure", text, 3)
        except Exception:
            pass
        self.trayIcon.setIcon(self.taskbarIconQuiescent)

    def changedRoomnames(self, newRoomnames):
        self.cache.putIntoCache("room_names", u",".join(newRoomnames), 60 * 60 * 24 * 365 * 5)
        self.chatparser.rooms = newRoomnames

    def showInfo(self):
        infoDialog = QtWidgets.QDialog(self)
        uic.loadUi(resourcePath("vi/ui/Info.ui"), infoDialog)
        infoDialog.versionLabel.setText(u"Version: {0}".format(vi.version.VERSION))
        infoDialog.logoLabel.setPixmap(QtGui.QPixmap(resourcePath("vi/ui/res/logo.png")))
        infoDialog.closeButton.clicked.connect(infoDialog.accept)
        infoDialog.show()

    def showSoundSetup(self):
        dialog = QtWidgets.QDialog(self)
        uic.loadUi(resourcePath("vi/ui/SoundSetup.ui"), dialog)
        dialog.volumeSlider.setValue(SoundManager().soundVolume)
        dialog.volumeSlider.valueChanged[int].connect(SoundManager().setSoundVolume)
        dialog.testSoundButton.clicked.connect(SoundManager().playSound)
        dialog.closeButton.clicked.connect(dialog.accept)
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

    def updateAvatarOnChatEntry(self, chatEntry, avatarData):
        updated = chatEntry.updateAvatar(avatarData)
        if not updated:
            self.avatarFindThread.addChatEntry(chatEntry, clearCache=True)
        else:
            self.avatar_loaded.emit(chatEntry.message.user, avatarData)

    def updateStatisticsOnMap(self, data):
        if not self.statisticsButton.isChecked():
            return
        if data["result"] == "ok":
            self.dotlan.addSystemStatistics(data["statistics"])
        elif data["result"] == "error":
            text = data["text"]
            self.trayIcon.showMessage("Loading statstics failed", text, 3)
            logging.error("updateStatisticsOnMap, error: %s" % text)

    def updateMapView(self):
        self.setMapContent(self.dotlan.svg)

    def zoomMapIn(self):
        self.mapView.setZoomFactor(self.mapView.zoomFactor() + 0.1)

    def zoomMapOut(self):
        self.mapView.setZoomFactor(self.mapView.zoomFactor() - 0.1)

    def logFileChanged(self, path, rescan=False):
        messages = self.chatparser.fileModified(path, rescan)
        for message in messages:
            # If players location has changed
            if message.status == states.LOCATION:
                self.knownPlayerNames.add(message.user)
                self.setLocation(message.user, message.systems[0])
            elif message.status == states.KOS_STATUS_REQUEST:
                # Do not accept KOS requests from any but monitored intel channels
                # as we don't want to encourage the use of xxx in those channels.
                if not message.room in self.roomnames:
                    text = message.message[4:]
                    text = text.replace("  ", ",")
                    parts = (name.strip() for name in text.split(","))
                    self.trayIcon.setIcon(self.taskbarIconWorking)
                    self.kosRequestThread.addRequest(parts, "xxx", False)
            # Otherwise consider it a 'normal' chat message
            elif message.user not in ("EVE-System", "EVE System") and message.status != states.IGNORE:
                self.addMessageToIntelChat(message, message.timestamp)
                # For each system that was mentioned in the message, check for alarm distance to the current system
                # and alarm if within alarm distance.
                systemList = self.dotlan.systems
                if message.systems:
                    for system in message.systems:
                        systemname = system.name
                        systemList[systemname].setStatus(message.status)
                        if message.status in (
                        states.REQUEST, states.ALARM) and message.user not in self.knownPlayerNames:
                            alarmDistance = self.alarmDistance if message.status == states.ALARM else 0
                            for nSystem, data in system.getNeighbours(alarmDistance).items():
                                distance = data["distance"]
                                chars = nSystem.getLocatedCharacters()
                                if len(chars) > 0 and message.user not in chars:
                                    self.trayIcon.showNotification(message, system.name, ", ".join(chars), distance)
                self.setMapContent(self.dotlan.svg)


class ChatroomsChooser(QtWidgets.QDialog):
    rooms_changed = pyqtSignal(list)

    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath("vi/ui/ChatroomsChooser.ui"), self)
        self.defaultButton.clicked.connect(self.setDefaults)
        self.cancelButton.clicked.connect(self.accept)
        self.saveButton.clicked.connect(self.saveClicked)
        cache = Cache()
        roomnames = cache.getFromCache("room_names")
        if not roomnames:
            roomnames = u"TheCitadel,North Provi Intel,4THINTEL"
        self.roomnamesField.setPlainText(roomnames)

    def saveClicked(self):
        text = str(self.roomnamesField.toPlainText())
        rooms = [str(name.strip()) for name in text.split(",")]
        self.accept()
        self.rooms_changed.emit(rooms)

    def setDefaults(self):
        self.roomnamesField.setPlainText(u"TheCitadel,North Provi Intel,4THINTEL")


class RegionChooser(QtWidgets.QDialog):
    new_region_chosen = pyqtSignal()

    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath("vi/ui/RegionChooser.ui"), self)
        self.cancelButton.clicked.connect(self.accept)
        self.saveButton.clicked.connect(self.saveClicked)
        cache = Cache()
        regionName = cache.getFromCache("region_name")
        if not regionName:
            regionName = u"Providence"
        self.regionNameField.setPlainText(regionName)

    def saveClicked(self):
        text = str(self.regionNameField.toPlainText())
        text = dotlan.convertRegionName(text)
        self.regionNameField.setPlainText(text)
        correct = False
        try:
            url = dotlan.Map.DOTLAN_BASIC_URL.format(text)
            content = requests.get(url).text
            if u"not found" in content:
                correct = False
                # Fallback -> ships vintel with this map?
                try:
                    with open(resourcePath("vi/ui/res/mapdata/{0}.svg".format(text))) as _:
                        correct = True
                except Exception as e:
                    logging.error(e)
                    correct = False
                if not correct:
                    QMessageBox.warning(self, u"No such region!", u"I can't find a region called '{0}'".format(text))
            else:
                correct = True
        except Exception as e:
            QMessageBox.critical(self, u"Something went wrong!", u"Error while testing existing '{0}'".format(str(e)))
            logging.error(e)
            correct = False
        if correct:
            Cache().putIntoCache("region_name", text, 60 * 60 * 24 * 365)
            self.accept()
            self.new_region_chosen.emit()


class SystemChat(QtWidgets.QDialog):
    SYSTEM = 0

    def __init__(self, parent, chatType, selector, chatEntries, knownPlayerNames):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath("vi/ui/SystemChat.ui"), self)
        self.parent = parent
        self.chatType = 0
        self.selector = selector
        self.chatEntries = []
        for entry in chatEntries:
            self.addChatEntry(entry)
        titleName = ""
        if self.chatType == SystemChat.SYSTEM:
            titleName = self.selector.name
            self.system = selector
        for name in knownPlayerNames:
            self.playerNamesBox.addItem(name)
        self.setWindowTitle("Chat for {0}".format(titleName))
        self.closeButton.clicked.connect(self.closeDialog)
        self.alarmButton.clicked.connect(self.setSystemAlarm)
        self.clearButton.clicked.connect(self.setSystemClear)
        self.locationButton.clicked.connect(self.locationSet)

    def _addMessageToChat(self, message, avatarPixmap):
        scrollToBottom = False
        if (self.chat.verticalScrollBar().value() == self.chat.verticalScrollBar().maximum()):
            scrollToBottom = True
        entry = ChatEntryWidget(message)
        entry.avatarLabel.setPixmap(avatarPixmap)
        listWidgetItem = QtWidgets.QListWidgetItem(self.chat)
        listWidgetItem.setSizeHint(entry.sizeHint())
        self.chat.addItem(listWidgetItem)
        self.chat.setItemWidget(listWidgetItem, entry)
        self.chatEntries.append(entry)
        entry.mark_system.connect(self.parent.markSystemOnMap)
        if scrollToBottom:
            self.chat.scrollToBottom()

    def addChatEntry(self, entry):
        if self.chatType == SystemChat.SYSTEM:
            message = entry.message
            avatarPixmap = entry.avatarLabel.pixmap()
            if self.selector in message.systems:
                self._addMessageToChat(message, avatarPixmap)

    def locationSet(self):
        char = str(self.playerNamesBox.currentText())
        self.location_set.emit(char, self.system.name)

    def newAvatarAvailable(self, charname, avatarData):
        for entry in self.chatEntries:
            if entry.message.user == charname:
                entry.updateAvatar(avatarData)

    def setSystemAlarm(self):
        self.system.setStatus(states.ALARM)
        self.parent.updateMapView()

    def setSystemClear(self):
        self.system.setStatus(states.CLEAR)
        self.parent.updateMapView()

    def closeDialog(self):
        self.accept()


class ChatEntryWidget(QtWidgets.QWidget):
    TEXT_SIZE = 11
    SHOW_AVATAR = True
    questionMarkPixmap = None

    mark_system = pyqtSignal(str)

    def __init__(self, message):
        QtWidgets.QWidget.__init__(self)
        if not self.questionMarkPixmap:
            self.questionMarkPixmap = QtGui.QPixmap(resourcePath("vi/ui/res/qmark.png")).scaledToHeight(32)
        uic.loadUi(resourcePath("vi/ui/ChatEntry.ui"), self)
        self.avatarLabel.setPixmap(self.questionMarkPixmap)
        self.message = message
        self.updateText()
        self.textLabel.linkActivated['QString'].connect(self.linkClicked)
        if sys.platform.startswith("win32") or sys.platform.startswith("cygwin"):
            ChatEntryWidget.TEXT_SIZE = 8
        self.changeFontSize(self.TEXT_SIZE)
        if not ChatEntryWidget.SHOW_AVATAR:
            self.avatarLabel.setVisible(False)

    def linkClicked(self, link):
        link = str(link)
        function, parameter = link.split("/", 1)
        if function == "mark_system":
            self.mark_system.emit(parameter)
        elif function == "link":
            webbrowser.open(parameter)

    def updateText(self):
        time = datetime.datetime.strftime(self.message.timestamp, "%H:%M:%S")
        text = u"<small>{time} - <b>{user}</b> - <i>{room}</i></small><br>{text}".format(user=self.message.user,
                                                                                         room=self.message.room,
                                                                                         time=time,
                                                                                         text=self.message.message)
        self.textLabel.setText(text)

    def updateAvatar(self, avatarData):
        image = QImage.fromData(avatarData)
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return False
        scaledAvatar = pixmap.scaled(32, 32)
        try:
            self.avatarLabel.setPixmap(scaledAvatar)
            return True
        except Exception as ex:
            # logging.warn("Updating a deleted chat item")
            self.avatarLabel = None
            self = None

    def changeFontSize(self, newSize):
        font = self.textLabel.font()
        font.setPointSize(newSize)
        self.textLabel.setFont(font)


class JumpbridgeChooser(QtWidgets.QDialog):
    set_jumpbridge_url = pyqtSignal(str)
    def __init__(self, parent, url):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath("vi/ui/JumpbridgeChooser.ui"), self)
        self.saveButton.clicked.connect(self.savePath)
        self.cancelButton.clicked.connect(self.accept)
        self.fileChooser.clicked.connect(self.choosePath)
        self.urlField.setText(url)
        # loading format explanation from textfile
        with open(resourcePath("docs/jumpbridgeformat.txt")) as f:
            self.formatInfoField.setPlainText(f.read())

    def savePath(self):

        try:
            url = str(self.urlField.text())
            self.set_jumpbridge_url.emit(url)
            self.accept()
        except Exception as e:
            QMessageBox.critical(None, "Finding Jumpbridgedata failed", "Error: {0}".format(str(e)))

    def choosePath(self):
        path = QFileDialog.getOpenFileName(self, caption="Open JB Text File")[0]
        self.urlField.setText(str(path))
