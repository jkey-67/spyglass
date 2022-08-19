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
import webbrowser
import datetime

from PySide6 import QtWidgets
from PySide6.QtCore import Signal as pyqtSignal
from vi.resources import resourcePath
from PySide6.QtGui import QImage, QPixmap
from vi.ui import Ui_ChatEntry


class ChatEntryWidget(QtWidgets.QWidget):
    TEXT_SIZE = 11
    DIM_IMG = 64
    SHOW_AVATAR = True
    questionMarkPixmap = None
    mark_system = pyqtSignal(str)

    def __init__(self, message):
        QtWidgets.QWidget.__init__(self)
        self.message = message
        self.ui = Ui_ChatEntry()
        self.ui.setupUi(self)
        if not self.questionMarkPixmap:
            self.questionMarkPixmap = QPixmap(resourcePath(os.path.join("vi", "ui", "res", "qmark.png"))).scaledToHeight(self.DIM_IMG)

        self.ui.avatarLabel.setPixmap(self.questionMarkPixmap)

        self.updateText()
        self.ui.textLabel.linkActivated['QString'].connect(self.linkClicked)
        self.changeFontSize(self.TEXT_SIZE)
        if not ChatEntryWidget.SHOW_AVATAR:
            self.ui.avatarLabel.setVisible(False)

    def __del__(self):
        logging.debug("ChatEntryWidget __del__ for message {}".format(self.message.message))

    def linkClicked(self, link):
        link = str(link)
        function, parameter = link.split("/", 1)
        if function == "mark_system":
            self.mark_system.emit(parameter)
        elif function == "link":
            webbrowser.open_new_tab(parameter)

    def updateText(self):
        time = datetime.datetime.strftime(self.message.timestamp, "%H:%M:%S")
        text = u"<small>{time} - <b>{user}</b> - <i>{room}</i></small><br>{text}".format(user=self.message.user,
                                                                                         room=self.message.room,
                                                                                         time=time,
                                                                                         text=self.message.message.rstrip(" \r\n").lstrip(" \r\n"))
        self.ui.textLabel.setText(text)

    def updateAvatar(self, avatar_data):
        image = QImage.fromData(avatar_data)
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return False
        scaled_avatar = pixmap.scaled(self.DIM_IMG, self.DIM_IMG)
        try:
            if self.ui.avatarLabel:
                self.ui.avatarLabel.setPixmap(scaled_avatar)
        except Exception :
            logging.warning("Updating a deleted chat item")
            self.ui.avatarLabel = None
            self = None
        return True

    def changeFontSize(self, newSize):
        font = self.ui.textLabel.font()
        font.setPointSize(newSize)
        self.ui.textLabel.setFont(font)
