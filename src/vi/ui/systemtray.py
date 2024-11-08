###########################################################################
#  Spyglass - Visual Intel Chat Analyzer                                  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.                                    #
#                                                                         #
#  This program is distributed in the hope that it will be useful,        #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the          #
#  GNU General Public License for more details.                           #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import time
import os

from PySide6 import QtWidgets
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon
from PySide6.QtCore import Signal
from PySide6.QtCore import QObject
from PySide6.QtGui import QDesktopServices
from vi.resources import resourcePath
from vi.states import States
from vi.ui.styles import Styles
from vi.soundmanager import SoundManager
from vi.cache import Cache
from vi.chatparser.message import Message, CTX


class ActionPackage(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.framelessCheck = QAction("Frameless Window", None, checkable=True)
        self.setDestination = QAction("Set Destination", None, checkable=False)
        self.addWaypoint = QAction("Add Waypoint", None, checkable=False)
        self.avoidSystem = QAction("Avoid System", None, checkable=False)
        self.clearJumpGate = QAction("Remove Ansiblex Jump Gate", None, checkable=False)
        self.clearAvoidList = QAction("Clear Avoid Systems", None, checkable=False)
        self.clearAll = QAction("Clear all Waypoints", None, checkable=False)
        self.openDotlan = QAction("Dotlan", None, checkable=False)
        self.openZKillboard = QAction("zKillbard", None, checkable=False)
        self.changeRegion = QAction("Change Region", None, checkable=False)
        self.alarmCheck = QAction("Show alarm notifications", None, checkable=True)
        self.quitAction = QAction("Quit", None)

        self.alarmDistance = list()

        for i in range(0, 6):
            action = QAction("{0} Jumps".format(i), None, checkable=True)
            if i == 0:
                action.setChecked(True)
            action.alarmDistance = i
            self.alarmDistance.append(action)

        self.currentSystem = None

        self.openDotlan.triggered.connect(self.browserOpenDotlan)
        self.openZKillboard.triggered.connect(self.browserOpenZKillboard)
        self.gameMenu = None

    def updateActionPackage(self, sys_name=None, rgn_name=None):
        self.currentSystem = sys_name
        if sys_name:
            self.gameMenu.setTitle("EVE-Online {}".format(sys_name.name))
            self.setDestination.setEnabled(True)
            self.addWaypoint.setEnabled(True)
            self.openDotlan.setEnabled(True)
            self.openZKillboard.setEnabled(True)
            self.avoidSystem.setEnabled(True)
            self.clearJumpGate.setEnabled(Cache().hasJumpGate(sys_name.name))
            self.currentSystem = sys_name
        else:
            self.gameMenu.setTitle("EVE-Online")
            self.setDestination.setEnabled(False)
            self.addWaypoint.setEnabled(False)
            self.openDotlan.setEnabled(False)
            self.openZKillboard.setEnabled(False)
            self.avoidSystem.setEnabled(False)
            self.clearJumpGate.setEnabled(False)
            self.currentSystem = None
        if rgn_name:
            self.changeRegion.setText("Change Region {}".format(rgn_name))
            self.changeRegion.setEnabled(True)
        else:
            self.changeRegion.setText("Change Region")
            self.changeRegion.setEnabled(False)

    def browserOpenDotlan(self):
        if self.currentSystem:
            QDesktopServices.openUrl("https://evemaps.dotlan.net/system/{}".format(self.currentSystem.name))

    def browserOpenZKillboard(self):
        if self.currentSystem:
            QDesktopServices.openUrl("https://zkillboard.com/system/{}".format(self.currentSystem.system_id))


class TrayContextMenu(QtWidgets.QMenu):
    instances = set()

    def __init__(self, tray_icon):
        """ trayIcon = the object with the methods to call
        """
        QtWidgets.QMenu.__init__(self)
        TrayContextMenu.instances.add(self)
        self.currentUser = None
        self.currentSystem = None
        self.trayIcon = tray_icon
        self.framelessCheck = QAction("Frameless Window", self, checkable=True)
        self.setDestination = QAction("Set Destination", None, checkable=False)
        self.addWaypoint = QAction("Add Waypoint", None, checkable=False)
        self.avoidSystem = QAction("Avoid System", None, checkable=False)
        self.clearJumpGate = QAction("Remove Ansiblex Jump Gate", None, checkable=False)
        self.clearAvoidList = QAction("Clear Avoid Systems", None, checkable=False)
        self.clearAll = QAction("Clear all Waypoints", None, checkable=False)
        self.openDotlan = QAction("Dotlan", None, checkable=False)
        self.openZKillboard = QAction("zKillbard", None, checkable=False)
        self.changeRegion = QAction("Change Region", None, checkable=False)
        self.alarmCheck = QAction("Show alarm notifications", self, checkable=True)
        self.quitAction = QAction("Quit", self)

        self.framelessCheck.triggered.connect(self.trayIcon.changeFrameless)
        self.addAction(self.framelessCheck)
        # self.addSeparator()
        # self.gameMenu = self.addMenu("EVE-Online")

        # self.gameMenu.addAction(self.setDestination)
        # self.gameMenu.addAction(self.addWaypoint)
        # self.gameMenu.addAction(self.avoidSystem)
        # self.gameMenu.addAction(self.clearAvoidList)
        # self.gameMenu.addAction(self.clearJumpGate)
        # self.gameMenu.addSeparator()
        # self.gameMenu.addAction(self.clearAll)
        # self.addMenu(self.gameMenu)
        # self.addSeparator()
        # self.addAction(self.openDotlan)
        # self.addAction(self.openZKillboard)
        # self.addAction(self.changeRegion)
        self.addSeparator()
        self.alarmCheck.setChecked(True)
        self.alarmCheck.triggered.connect(self.trayIcon.switchAlarm)
        self.addAction(self.alarmCheck)
        distance_menu = self.addMenu("Alarm Distance")
        self.distanceGroup = QActionGroup(self)
        for i in range(0, 6):
            action = QAction("{0} Jumps".format(i), None, checkable=True)
            if i == 0:
                action.setChecked(True)
            action.alarmDistance = i
            action.triggered.connect(self.changeAlarmDistance)
            self.distanceGroup.addAction(action)
            distance_menu.addAction(action)
        self.addMenu(distance_menu)
        self.addSeparator()
        self.quitAction.triggered.connect(self.trayIcon.quit)
        self.addAction(self.quitAction)

    def updateMenu(self, sys_name=None, rgn_name=None):
        self.currentSystem = sys_name
        if sys_name:
            self.gameMenu.setTitle("EVE-Online {}".format(sys_name.name))
            self.setDestination.setEnabled(True)
            self.addWaypoint.setEnabled(True)
            self.openDotlan.setEnabled(True)
            self.openZKillboard.setEnabled(True)
            self.avoidSystem.setEnabled(True)
            self.clearJumpGate.setEnabled(Cache().hasJumpGate(sys_name.name))
            self.currentSystem = sys_name
        else:
            self.gameMenu.setTitle("EVE-Online")
            self.setDestination.setEnabled(False)
            self.addWaypoint.setEnabled(False)
            self.openDotlan.setEnabled(False)
            self.openZKillboard.setEnabled(False)
            self.avoidSystem.setEnabled(False)
            self.clearJumpGate.setEnabled(False)
            self.currentSystem = None
        if rgn_name:
            self.changeRegion.setText("Change Region {}".format(rgn_name))
            self.changeRegion.setEnabled(True)
        else:
            self.changeRegion.setText("Change Region")
            self.changeRegion.setEnabled(False)

    def changeAlarmDistance(self):
        for action in self.distanceGroup.actions():
            if action.isChecked():
                self.trayIcon.alarmDistance = action.alarmDistance
                self.trayIcon.changeAlarmDistance()


class MapContextMenu(QtWidgets.QMenu):

    alarm_distance = Signal(int)

    def __init__(self):
        QtWidgets.QMenu.__init__(self)
        self.currentUser = None
        self.currentSystem = None
        self.alarmDistance = 2
        self.framelessCheck = QAction("Frameless Window", self, checkable=True)
        self.openDotlan = QAction("Dotlan", None, checkable=False)
        self.openZKillboard = QAction("zKillbard", None, checkable=False)
        self.changeRegion = QAction("Change Region", None, checkable=False)
        self.alarmCheck = QAction("Show alarm notifications", self, checkable=True)
        self.clearJumpGate = QAction("Remove Ansiblex Jump Gate", None, checkable=False)

        self.addAction(self.framelessCheck)
        self.addSeparator()
        self.gameMenu = PlayerContextMenu(Cache().getAPICharNames())
        self.addMenu(self.gameMenu)
        self.addSeparator()
        self.addAction(self.openDotlan)
        self.addAction(self.openZKillboard)
        self.addAction(self.changeRegion)
        self.addSeparator()
        self.alarmCheck.setChecked(True)
        self.addAction(self.alarmCheck)
        distance_menu = self.addMenu("Alarm Distance")
        self.distanceGroup = QActionGroup(self)
        for i in range(0, 6):
            action = QAction("{0} Jumps".format(i), None, checkable=True)
            if i == self.alarm_distance:
                action.setChecked(True)
            action.alarmDistance = i
            action.triggered.connect(self.changeAlarmDistance)
            self.distanceGroup.addAction(action)
            distance_menu.addAction(action)
        self.addMenu(distance_menu)
        self.addSeparator()
        self.addAction(self.clearJumpGate)
        self.addSeparator()
        self.quitAction = QAction("Quit", self)
        self.addAction(self.quitAction)

        self.openDotlan.triggered.connect(self.browserOpenDotlan)
        self.openZKillboard.triggered.connect(self.browserOpenZKillboard)

    def updateMenu(self, sys_name=None, rgn_name=None, alarm_distance=2):
        self.alarmDistance = alarm_distance
        for action in self.distanceGroup.actions():
            action.setChecked(action.alarmDistance == self.alarmDistance)

        if sys_name:
            self.gameMenu.setTitle("EVE-Online {}".format(sys_name.name))
            self.gameMenu.setEnabled(True)
            self.openDotlan.setEnabled(True)
            self.openZKillboard.setEnabled(True)
            self.clearJumpGate.setEnabled(Cache().hasJumpGate(sys_name.name))
            self.currentSystem = sys_name
        else:
            self.gameMenu.setTitle("EVE-Online")
            self.gameMenu.setEnabled(False)
            self.openDotlan.setEnabled(False)
            self.openZKillboard.setEnabled(False)
            self.clearJumpGate.setEnabled(False)
            self.currentSystem = None
        if rgn_name:
            self.changeRegion.setText("Change Region {}".format(rgn_name))
            self.changeRegion.setEnabled(True)
        else:
            self.changeRegion.setText("Change Region")
            self.changeRegion.setEnabled(False)

    def changeAlarmDistance(self):
        for action in self.distanceGroup.actions():
            if action.isChecked():
                self.alarm_distance.emit(action.alarmDistance)

    def browserOpenDotlan(self):
        if self.currentSystem:
            QDesktopServices.openUrl("https://evemaps.dotlan.net/system/{}".format(self.currentSystem.name))

    def browserOpenZKillboard(self):
        if self.currentSystem:
            QDesktopServices.openUrl(
                "https://zkillboard.com/system/{}".format(self.currentSystem.system_id))


class JumpBridgeContextMenu(QtWidgets.QMenu):
    def __init__(self, src=None, dst=None):
        QtWidgets.QMenu.__init__(self)
        self.update = QAction("Update Jump Bridge Data")
        self.delete = QAction("Delete the Jump Bridge")
        if src:
            self.selectRegionSrc = QAction("Show System {} on map".format(src))
        else:
            self.selectRegionSrc = QAction("Show Source System on map")
        if dst:
            self.selectRegionDst = QAction("Show System {} on map".format(dst))
        else:
            self.selectRegionDst = QAction("Show Destination System on map")
        self.player_menu = PlayerContextMenu(Cache().getAPICharNames())
        self.insertMenu(None, self.player_menu)
        self.addSeparator()
        self.addAction(self.selectRegionSrc)
        self.addAction(self.selectRegionDst)
        self.addSeparator()
        self.addAction(self.update)
        self.addAction(self.delete)


class POIContextMenu(QtWidgets.QMenu):
    def __init__(self, region_name=None, system_name=None):
        QtWidgets.QMenu.__init__(self)
        self.delete = QAction("Remove the selected POI")
        self.copy = QAction("Selected POI to clipboard")
        self.copy_all = QAction("All POIs to clipboard")
        self.player_menu = PlayerContextMenu(Cache().getAPICharNames())
        self.insertMenu(None, self.player_menu)
        self.addAction(self.copy)
        self.addAction(self.copy_all)
        if system_name:
            self.selectRegion = QAction("Show System {} on map".format(system_name))
        else:
            self.selectRegion = QAction("Show System on map")
        self.addAction(self.selectRegion)
        self.addSeparator()
        self.addAction(self.delete)


class TheraContextMenu(QtWidgets.QMenu):
    def __init__(self, system_name=None):
        QtWidgets.QMenu.__init__(self)
        self.player_menu = PlayerContextMenu(Cache().getAPICharNames())
        self.insertMenu(None, self.player_menu)
        if system_name:
            self.selectRegion = QAction("Show System {} on map".format(system_name))
        else:
            self.selectRegion = QAction("Show System on map")
        self.addAction(self.selectRegion)
        self.updateData = QAction("Fetch data from EvE-Scout")
        self.addSeparator()
        self.addAction(self.updateData)


class PlayerContextMenu(QtWidgets.QMenu):
    def __init__(self, players: list):
        QtWidgets.QMenu.__init__(self, title="EVE-Online Actions")
        self.new_player = list()
        self.no_char = QAction("No registered characters", None, checkable=False)
        if len(players) == 0:
            self.addAction(self.no_char)
        else:
            for player in players:
                new_player_actions = {
                                "menu": QtWidgets.QMenu(player),
                                "destination": QAction("Set Destination", None, checkable=False),
                                "waypoint": QAction("Add Waypoint", None, checkable=False),
                                # "route": QAction("Set Route", None, checkable=False),
                                "clearall": QAction("Clear all Waypoints", None, checkable=False)
                            }
                new_player_actions["destination"].eve_action = {"player_name": player, "action": "destination"}
                new_player_actions["waypoint"].eve_action = {"player_name": player, "action": "waypoint"}
                # new_player_actions["route"].eve_action = {"player_name": player, "action": "route"}
                # new_player_actions["route"].setToolTip("Sets a route using defined Spyglass jump bridges")
                new_player_actions["clearall"].eve_action = {"player_name": player, "action": "clearall"}
                new_player_actions["clearall"].setToolTip("Clears all way points")
                new_player_menu = new_player_actions["menu"]
                new_player_menu.addAction(new_player_actions["destination"])
                new_player_menu.addAction(new_player_actions["waypoint"])
                # new_player_menu.addAction(new_player_actions["route"])
                new_player_menu.addAction(new_player_actions["clearall"])
                new_player_menu.setStyleSheet(Styles.getStyle())
                self.new_player.append(new_player_actions)
                self.addMenu(new_player_menu)

        self.setStyleSheet(Styles.getStyle())


class TrayIcon(QtWidgets.QSystemTrayIcon):
    # Min seconds between two notifications
    MIN_WAIT_NOTIFICATION = 15

    alarm_distance = Signal(int)
    change_frameless = Signal()
    quit_signal = Signal()

    def __init__(self, app):
        self.icon = QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")))
        QSystemTrayIcon.__init__(self, self.icon, app)
        self.setToolTip("Your Spyglass Information Service! :)")
        self.lastNotifications = {}
        self.setContextMenu(TrayContextMenu(self))
        self.showAlarm = True
        self.showRequest = True
        self.alarmDistance = 0

    def changeAlarmDistance(self):
        distance = self.alarmDistance
        self.alarm_distance.emit(distance)

    def changeFrameless(self):
        self.change_frameless.emit()

    @property
    def distanceGroup(self):
        return self.contextMenu().distanceGroup

    def quit(self):
        self.quit_signal.emit()

    def switchAlarm(self):
        new_value = not self.showAlarm
        for cm in TrayContextMenu.instances:
            cm.alarmCheck.setChecked(new_value)
        self.showAlarm = new_value

    def showNotification(self, message: Message, system, char, distance):
        if message is None:
            return
        room = message.roomName
        title = None
        text = None
        icon = None
        text = ""

        if (message.status == States.ALARM and
                self.showAlarm and
                self.lastNotifications.get(States.ALARM, 0) < time.time() - self.MIN_WAIT_NOTIFICATION):
            title = "ALARM!"
            icon = 2
            speech_text = (u"System {0} Alarm distance {1} in Room {2}, {3} jumps away from {4}".format(
                system, distance, room, distance, char))
            text = speech_text + (u"\nText: %s" % text)
            SoundManager().playSound("alarm_{}".format(distance), text, "" if message.roomName != CTX.ZKILLBOARD_ROOM_NAME else speech_text)
            self.lastNotifications[States.ALARM] = time.time()
        elif (message.status == States.REQUEST and
              self.showRequest and
              self.lastNotifications.get(States.REQUEST, 0) < time.time() - self.MIN_WAIT_NOTIFICATION):
            title = "Status request"
            icon = 1
            text = (u"Someone is requesting status of {0} in {1}.".format(system, room))
            self.lastNotifications[States.REQUEST] = time.time()
            # SoundManager().playSound("request", text)
        if not (title is None or text is None or icon):
            text = text.format(**locals())
            self.showMessage(title=title, msg=text, icon=icon)
