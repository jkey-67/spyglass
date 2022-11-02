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
from PySide6.QtCore import Signal as pyqtSignal

from vi.resources import resourcePath
from vi import states
from vi.ui.styles import Styles
from vi.soundmanager import SoundManager
from vi.cache import Cache

class TrayContextMenu(QtWidgets.QMenu):
    instances = set()

    def __init__(self, trayIcon):
        """ trayIcon = the object with the methods to call
        """
        QtWidgets.QMenu.__init__(self)
        TrayContextMenu.instances.add(self)
        self.currentUser = None
        self.currentSystem = None
        self.trayIcon = trayIcon
        self._buildMenu()

    def hasJumpGate(sys_name=None) -> bool:
        return False

    def updateMenu(self, sys_name=None, rgn_name=None):
        if sys_name:
            self.gameMenu.setTitle("EVE-Online {}".format(sys_name.name))
            self.setDestination.setEnabled(True)
            self.addWaypoint.setEnabled(True)
            self.openDotlan.setEnabled(True)
            self.openZKillboard.setEnabled(True)
            self.avoidSystem.setEnabled(True)
            self.clearJumpGate.setEnabled(self.hasJumpGate(sys_name.name))
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

    def _buildMenu(self):
        self.framelessCheck = QAction("Frameless Window", self, checkable=True)
        self.framelessCheck.triggered.connect(self.trayIcon.changeFrameless)
        self.addAction(self.framelessCheck)
        self.addSeparator()
        self.gameMenu = self.addMenu("EVE-Online")
        self.setDestination = QAction("Set Destination", None, checkable=False)
        self.addWaypoint = QAction("Add Waypoint", None, checkable=False)
        self.avoidSystem = QAction("Avoid System", None, checkable=False)
        self.clearJumpGate = QAction("Remove Ansiblex Jump Gate", None, checkable=False)
        self.clearAvoidList = QAction("Clear Avoid Systems", None, checkable=False)
        self.clearAll = QAction("Clear all Waypoints", None, checkable=False)
        self.gameMenu.addAction(self.setDestination)
        self.gameMenu.addAction(self.addWaypoint)
        self.gameMenu.addAction(self.avoidSystem)
        self.gameMenu.addAction(self.clearAvoidList)
        self.gameMenu.addAction(self.clearJumpGate)
        self.gameMenu.addSeparator()
        self.gameMenu.addAction(self.clearAll)
        self.addMenu(self.gameMenu)
        self.addSeparator()
        self.openDotlan = QAction("Dotlan", None, checkable=False)
        self.addAction(self.openDotlan)
        self.openZKillboard = QAction("zKillbard", None, checkable=False)
        self.addAction(self.openZKillboard)
        self.changeRegion = QAction("Change Region", None, checkable=False)
        self.addAction(self.changeRegion)
        self.addSeparator()
        self.alarmCheck = QAction("Show alarm notifications", self, checkable=True)
        self.alarmCheck.setChecked(True)
        self.alarmCheck.triggered.connect(self.trayIcon.switchAlarm)
        self.addAction(self.alarmCheck)
        distanceMenu = self.addMenu("Alarm Distance")
        self.distanceGroup = QActionGroup(self)
        for i in range(0, 6):
            action = QAction("{0} Jumps".format(i), None, checkable=True)
            if i == 0:
                action.setChecked(True)
            action.alarmDistance = i
            action.triggered.connect(self.changeAlarmDistance)
            self.distanceGroup.addAction(action)
            distanceMenu.addAction(action)
        self.addMenu(distanceMenu)
        self.addSeparator()
        self.quitAction = QAction("Quit", self)
        self.quitAction.triggered.connect(self.trayIcon.quit)
        self.addAction(self.quitAction)

    def changeAlarmDistance(self):
        for action in self.distanceGroup.actions():
            if action.isChecked():
                self.trayIcon.alarmDistance = action.alarmDistance
                self.trayIcon.changeAlarmDistance()


class JumpBridgeContextMenu(QtWidgets.QMenu):
    def __init__(self):
        QtWidgets.QMenu.__init__(self)
        self.update = QAction("Update Jump Bridge Data")
        self.delete = QAction("Delete the Jump Bridge")
        self.player_menu = PlayerContextMenu(Cache().getActivePlayerNames())
        self.insertMenu(None, self.player_menu)
        self.addSeparator()
        self.addAction(self.update)
        self.addAction(self.delete)


class POIContextMenu(QtWidgets.QMenu):
    def __init__(self):
        QtWidgets.QMenu.__init__(self)
        self.delete = QAction("Delete the POI")
        self.player_menu = PlayerContextMenu(Cache().getActivePlayerNames())
        self.insertMenu(None, self.player_menu)
        self.addSeparator()
        self.addAction(self.delete)


class TheraContextMenu(QtWidgets.QMenu):
    def __init__(self):
        QtWidgets.QMenu.__init__(self)
        self.player_menu = PlayerContextMenu(Cache().getActivePlayerNames())
        self.insertMenu(None, self.player_menu)
        self.updateData = QAction("Update Thera Connections")
        self.addSeparator()
        self.addAction(self.updateData)


class PlayerContextMenu(QtWidgets.QMenu):
    def __init__(self, players: list):
        QtWidgets.QMenu.__init__(self, title="EVE-Online Actions")
        self.new_player = list()

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
            new_player_menu.setStyleSheet(Styles().getStyle())
            self.new_player.append(new_player_actions)
            self.addMenu(new_player_menu)

        self.setStyleSheet(Styles().getStyle())


class TrayIcon(QtWidgets.QSystemTrayIcon):
    # Min seconds between two notifications
    MIN_WAIT_NOTIFICATION = 15

    alarm_distance = pyqtSignal(int)
    change_frameless = pyqtSignal()
    quit_signal = pyqtSignal()

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

    def showNotification(self, message, system, char, distance):
        if message is None:
            return
        room = message.room
        title = None
        text = None
        icon = None
        text = ""

        if (message.status == states.ALARM and
                self.showAlarm and
                self.lastNotifications.get(states.ALARM, 0) < time.time() - self.MIN_WAIT_NOTIFICATION):
            title = "ALARM!"
            icon = 2
            speech_text = (u"System {0} Alarm distance {1} in Room {2}, {3} jumps away from {4}".format(
                system, distance, room, distance, char))
            text = speech_text + (u"\nText: %s" % text)
            SoundManager().playSound("alarm_{}".format(distance), text, speech_text)
            self.lastNotifications[states.ALARM] = time.time()
        elif (message.status == states.REQUEST and
              self.showRequest and
              self.lastNotifications.get(states.REQUEST, 0) < time.time() - self.MIN_WAIT_NOTIFICATION):
            title = "Status request"
            icon = 1
            text = (u"Someone is requesting status of {0} in {1}.".format(system, room))
            self.lastNotifications[states.REQUEST] = time.time()
            # SoundManager().playSound("request", text)
        if not (title is None or text is None or icon):
            text = text.format(**locals())
            self.showMessage(title, text, icon)

