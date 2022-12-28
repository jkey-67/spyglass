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

from vi.cache import Cache
from PySide6 import QtWidgets
from PySide6.QtCore import Signal as pyqtSignal
from vi.ui import Ui_ChatroomsChooser
from PySide6.QtGui import Qt


class ChatroomChooser(QtWidgets.QDialog):
    rooms_changed = pyqtSignal(list)
    DEFAULT_ROOM_MANES = [u"Scald Intel", u"FI.RE Intel", u"Outer-Core Intel"]

    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_ChatroomsChooser()
        self.ui.setupUi(self)
        self.ui.defaultButton.clicked.connect(self.setDefaults)
        self.ui.saveButton.clicked.connect(self.saveClicked)
        room_names = Cache().getFromCache("room_names")
        if not room_names:
            room_names = u','.join(ChatroomChooser.DEFAULT_ROOM_MANES)
        self.ui.roomnamesField.setPlainText(room_names)
        # self.setWindowFlags(Qt.Popup)

    def saveClicked(self):
        text = str(self.ui.roomnamesField.toPlainText())
        rooms = [str(name.strip()) for name in text.split(",")]
        self.accept()
        self.rooms_changed.emit(rooms)

    def setDefaults(self):
        self.ui.roomnamesField.setPlainText(u','.join(ChatroomChooser.DEFAULT_ROOM_MANES))



