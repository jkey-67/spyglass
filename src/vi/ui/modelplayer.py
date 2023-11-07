###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool@gmx.net)                   #
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

from typing import Union
from PySide6.QtGui import *
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QStyledItemDelegate

from vi import evegate

from vi.cache.cache import Cache
from PySide6.QtSql import QSqlQueryModel


class TableModelPlayers(QSqlQueryModel):
    def __init__(self, parent=None):
        super(TableModelPlayers, self).__init__(parent)

    def flags(self, index) -> QtCore.Qt.ItemFlags:
        if index.column() == 1:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled


class StyledItemDelegatePlayers(QStyledItemDelegate):
    players_edit_changed = pyqtSignal()

    def __init__(self, parent=None):
        super(StyledItemDelegatePlayers, self).__init__(parent)
        self.cache = Cache()

    def paint(self, painter, option, index):
        super(StyledItemDelegatePlayers, self).paint(painter, option, index)
        return
        painter.save()
        if index.column() == 0:
            type_id = index.data()
            type_data = evegate.getTypesIcon(type_id)
            img = QImage.fromData(type_data)
            painter.setClipRect(option.rect)
            painter.drawImage(option.rect.topLeft(), img)
        else:
            super(StyledItemDelegatePlayers, self).paint(painter, option, index)
        painter.restore()

    def createEditor(self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem,
                     index: Union[
                         QtCore.QModelIndex, QtCore.QPersistentModelIndex]) -> QtWidgets.QWidget:
        if index.column() == 1:
            itm = QtWidgets.QComboBox(parent)
            itm.setEditable(False)
            itm.setFrame(False)
            itm.setMaxVisibleItems(1)
            itm.addItem("Yes")
            itm.addItem("No")
            return itm
        else:
            return super(StyledItemDelegatePlayers, self).createEditor(parent, option, index)

    def setEditorData(self, editor, index) -> None:
        if index.column() == 1:
            data = index.data()
            idx = editor.findText(data)
            if idx >= 0:
                editor.setCurrentIndex(idx)
        else:
            super(StyledItemDelegatePlayers, self).setEditorData(editor, index)

    def setModelData(self, editor, model, index) -> None:
        if editor.currentText() != index.data():
            inx_data = editor.currentText()
            inx_name = model.index(index.row(),0).data()
            used_player_names = self.cache.getActivePlayerNames()
            if inx_data == "Yes":
                used_player_names.add(inx_name)
            else:
                if inx_name in used_player_names:
                    used_player_names.remove(inx_name)
            self.cache.setActivePlayerNames(used_player_names)
            super(StyledItemDelegatePlayers, self).setModelData(editor, model, index)
            self.players_edit_changed.emit()
