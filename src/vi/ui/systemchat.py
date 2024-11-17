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

from PySide6 import QtWidgets
from PySide6.QtCore import Signal
from PySide6.QtGui import QDesktopServices
from vi.ui import Ui_SystemChat
from vi.ui.chatentrywidget import ChatEntryWidget
from .chatentrywidget import ChatEntryItem


class SystemChat(QtWidgets.QDialog):
    SYSTEM = 0
    location_set = Signal(str, str)
    repaint_needed = Signal()

    def __init__(self, parent, chat_type, selector, chat_entries, known_player_names):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_SystemChat()
        self.ui.setupUi(self)
        self.chatType = chat_type
        self.selector = selector
        self.chatEntries = []
        for entry in chat_entries:
            self.addChatEntry(entry)
        title_name = ""
        if self.chatType == SystemChat.SYSTEM:
            title_name = self.selector.name
            self.system = selector
        for name in known_player_names:
            self.ui.playerNamesBox.addItem(name)
        self.setWindowTitle("Chat for {0}".format(title_name))
        self.ui.closeButton.clicked.connect(self.closeDialog)
        self.ui.alarmButton.clicked.connect(self.setSystemAlarm)
        self.ui.clearButton.clicked.connect(self.setSystemClear)
        self.ui.locationButton.clicked.connect(self.locationSet)
        self.ui.openzKillboard.clicked.connect(self.openzKillboard)
        self.ui.dotlanButton.clicked.connect(self.openDotlan)

    def _addMessageToChat(self, message, avatar_pixmap):
        scroll_to_bottom = False
        if self.ui.chat.verticalScrollBar().value() == self.ui.chat.verticalScrollBar().maximum():
            scroll_to_bottom = True
        entry = ChatEntryWidget(message)
        entry.ui.avatarLabel.setPixmap(avatar_pixmap)

        list_widget_item = ChatEntryItem(
            key=message.timestamp.strftime("%Y%m%d %H%M%S"),
            listview=self.ui.chat)

        list_widget_item.setSizeHint(entry.sizeHint())
        self.ui.chat.addItem(list_widget_item)
        self.ui.chat.setItemWidget(list_widget_item, entry)
        self.chatEntries.append(entry)

        if scroll_to_bottom:
            self.ui.chat.scrollToBottom()

    def addChatEntry(self, entry):
        if self.chatType == SystemChat.SYSTEM:
            message = entry.message
            avatar_pixmap = entry.ui.avatarLabel.pixmap()
            if self.selector in message.affectedSystems:
                self._addMessageToChat(message, avatar_pixmap)

    def openDotlan(self):
        url = "https://evemaps.dotlan.net/system/{system}".format(system=self.system.name)
        QDesktopServices.openUrl(url)

    def openzKillboard(self):
        url = "https://zkillboard.com/system/{system}/".format(system=self.system.system_id)
        QDesktopServices.openUrl(url)

    def locationSet(self):
        char = str(self.ui.playerNamesBox.currentText())
        self.location_set.emit(char, self.system.name)

    def newAvatarAvailable(self, avatar_name, avatar_data):
        for entry in self.chatEntries:
            if entry.message.user == avatar_name:
                entry.updateAvatar(avatar_data)

    def setSystemAlarm(self):
        # self.system.setStatus(States.ALARM, datetime.datetime.now(datetime.UTC))
        self.repaint_needed.emit()

    def setSystemClear(self):
        # self.system.setStatus(States.CLEAR, datetime.datetime.now(datetime.UTC))
        self.repaint_needed.emit()

    def closeDialog(self):
        self.accept()
