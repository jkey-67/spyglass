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

import os
import logging
import datetime

from PySide6 import QtWidgets
from PySide6.QtCore import Signal as pyqtSignal
from vi.resources import resourcePath
from PySide6.QtGui import QImage, QPixmap, QDesktopServices
from vi.ui import Ui_ChatEntry
from vi.chatparser.message import Message


class ChatEntryItem(QtWidgets.QListWidgetItem):

    def __init__(self, key, **kwargs):
        """
            Initialize the chat entry with sort key
        Args:
            key: sorting key for list ordering
            **kwargs:
        """
        QtWidgets.QListWidgetItem.__init__(self, **kwargs)
        self.key = key

    def __lt__(self, other):
        if hasattr(other, "key") and self.key:
            return self.key < other.key
        else:
            return False


class ChatEntryWidget(QtWidgets.QWidget):
    TEXT_SIZE = 11
    DIM_IMG = 64
    SHOW_AVATAR = True
    questionMarkPixmap = None
    mark_system = pyqtSignal(str)

    def __init__(self, message: Message):
        QtWidgets.QWidget.__init__(self)
        self.message = message
        self.ui = Ui_ChatEntry()
        self.ui.setupUi(self)
        if self.message.roomName == "zKillboard":
            self.questionMarkPixmap = QPixmap(
                resourcePath(os.path.join("vi", "ui", "res", "zKillboard.svg"))).scaledToHeight(self.DIM_IMG)
        elif not self.questionMarkPixmap:
            self.questionMarkPixmap = QPixmap(
                resourcePath(os.path.join("vi", "ui", "res", "qmark.png"))).scaledToHeight(self.DIM_IMG)

        self.ui.avatarLabel.setPixmap(self.questionMarkPixmap)

        self.updateText()
        self.ui.textLabel.linkActivated['QString'].connect(self.linkClicked)
        self.changeFontSize(self.TEXT_SIZE)
        if not ChatEntryWidget.SHOW_AVATAR:
            self.ui.avatarLabel.setVisible(False)

    def __del__(self):
        logging.debug("ChatEntryWidget __del__ for message {}".format(self.message.guiText))

    def linkClicked(self, link):
        link = str(link)
        function, parameter = link.split("/", 1)
        if function == "mark_system":
            self.mark_system.emit(parameter)
        elif function == "link":
            QDesktopServices.openUrl(parameter)

    def updateText(self):
        time = datetime.datetime.strftime(self.message.timestamp, "%H:%M:%S")
        text = u"<small>{time} - <b>{user}</b> - <i>{room}</i></small><br>{text}".format(
            user=self.message.user,
            room=self.message.roomName,
            time=time,
            text=self.message.guiText.rstrip("\r\n").lstrip("\r\n"))
        self.ui.textLabel.setText(text)

    def updateAvatar(self, avatar_data) -> bool:
        """
            Updates the label image of the chat-entry widget
        Args:
            avatar_data: blob of the image

        Returns:
            False: if no image could be loaded from the blob
        """
        if type(avatar_data) is QImage:
            image = avatar_data
        elif type(avatar_data) is bytes:
            image = QImage.fromData(avatar_data)
        elif type(avatar_data) is str:
            image = QImage(avatar_data)
        else:
            return False

        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return False
        scaled_avatar = pixmap.scaled(self.DIM_IMG, self.DIM_IMG)
        try:
            if self.ui.avatarLabel:
                self.ui.avatarLabel.setPixmap(scaled_avatar)
        except (Exception,):
            logging.warning("Updating a deleted chat item")
            self.ui.avatarLabel = None
            # self = None
        return True

    def changeFontSize(self, size):
        font = self.ui.textLabel.font()
        font.setPointSize(size)
        self.ui.textLabel.setFont(font)
