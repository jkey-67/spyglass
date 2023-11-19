###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool @ gmx.net)                 #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify   #
#  it under the terms of the GNU General Public License as published by   #
#  the Free Software Foundation, either version 3 of the License, or      #
#  (at your option) any later version.                                    #
#                                                                         #
#  This program is distributed in the hope that it will be useful,        #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           #
#  GNU General Public License for more details.                           #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License      #
#  along with this program. If not, see <https://www.gnu.org/licenses/>.  #
###########################################################################

import datetime

from PySide6 import QtWidgets
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtGui import QDesktopServices
from vi import states
from vi.ui import Ui_SystemChat
from vi.ui.chatentrywidget import ChatEntryWidget
from .chatentrywidget import ChatEntryItem


class SystemChat(QtWidgets.QDialog):
    SYSTEM = 0
    location_set = pyqtSignal(str, str)
    repaint_needed = pyqtSignal()

    def __init__(self, parent, chatType, selector, chatEntries, knownPlayerNames):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_SystemChat()
        self.ui.setupUi(self)
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
            self.ui.playerNamesBox.addItem(name)
        self.setWindowTitle("Chat for {0}".format(titleName))
        self.ui.closeButton.clicked.connect(self.closeDialog)
        self.ui.alarmButton.clicked.connect(self.setSystemAlarm)
        self.ui.clearButton.clicked.connect(self.setSystemClear)
        self.ui.locationButton.clicked.connect(self.locationSet)
        self.ui.openzKillboard.clicked.connect(self.openzKillboard)
        self.ui.dotlanButton.clicked.connect(self.openDotlan)

    def _addMessageToChat(self, message, avatarPixmap):
        scrollToBottom = False
        if self.ui.chat.verticalScrollBar().value() == self.ui.chat.verticalScrollBar().maximum():
            scrollToBottom = True
        entry = ChatEntryWidget(message)
        entry.ui.avatarLabel.setPixmap(avatarPixmap)

        listWidgetItem = ChatEntryItem(
            sortkey=message.timestamp.strftime("%Y%m%d %H%M%S"),
            listview=self.ui.chat)

        listWidgetItem.setSizeHint(entry.sizeHint())
        self.ui.chat.addItem(listWidgetItem)
        self.ui.chat.setItemWidget(listWidgetItem, entry)
        self.chatEntries.append(entry)

        if scrollToBottom:
            self.ui.chat.scrollToBottom()

    def addChatEntry(self, entry):
        if self.chatType == SystemChat.SYSTEM:
            message = entry.message
            avatarPixmap = entry.ui.avatarLabel.pixmap()
            if self.selector in message.affectedSystems:
                self._addMessageToChat(message, avatarPixmap)

    def openDotlan(self):
        url = "https://evemaps.dotlan.net/system/{system}".format(system=self.system.name)
        QDesktopServices.openUrl(url)

    def openzKillboard(self):
        url = "https://zkillboard.com/system/{system}/".format(system=self.system.systemId)
        QDesktopServices.openUrl(url)

    def locationSet(self):
        char = str(self.ui.playerNamesBox.currentText())
        self.location_set.emit(char, self.system.name)

    def newAvatarAvailable(self, charname, avatarData):
        for entry in self.chatEntries:
            if entry.message.user == charname:
                entry.updateAvatar(avatarData)

    def setSystemAlarm(self):
        self.system.setStatus(states.ALARM, datetime.datetime.utcnow())
        self.repaint_needed.emit()

    def setSystemClear(self):
        self.system.setStatus(states.CLEAR, datetime.datetime.utcnow())
        self.repaint_needed.emit()

    def closeDialog(self):
        self.accept()


