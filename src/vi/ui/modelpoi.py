###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2024 Nele McCool (nele.mccool @ gmx.net)                 #
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

import json
from typing import Union
from vi import evegate
from vi.cache.cache import Cache
from PySide6.QtGui import Qt
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlQueryModel
from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtGui import QImage


class POITableModel(QSqlQueryModel):
    poi_order_changed = Signal()

    def __init__(self, parent=None):
        super(POITableModel, self).__init__(parent)
        self.cache = Cache()

    def flags(self, index) -> Qt.ItemFlags:
        default_flags = super(POITableModel, self).flags(index)
        if index.isValid():
            if index.column() == 1:
                return Qt.ItemIsDragEnabled | Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable | default_flags
            else:
                return Qt.ItemIsDragEnabled | Qt.ItemIsSelectable | Qt.ItemIsEnabled | default_flags
        else:
            return Qt.ItemIsDropEnabled | default_flags

    def supportedDropActions(self):
        return Qt.MoveAction | Qt.CopyAction

    def dropMimeData(self, data: QtCore.QMimeData, action: Qt.DropAction, row: int, column: int, parent) -> bool:
        if action == Qt.IgnoreAction:
            return True
        if not data.hasFormat('text/plain'):
            return False

        encoded_data = data.data('text/plain')
        src_data = json.loads(str(encoded_data.data(), encoding='utf-8'))[0]
        dst_data = self.cache.getPOIAtIndex(row)
        self.cache.swapPOIs(src=src_data["sid"], dst=dst_data["sid"])
        self.poi_order_changed.emit()
        return True

    def mimeTypes(self):
        return ['text/plain']

    def mimeData(self, indexes):
        mime_data = QtCore.QMimeData()
        mime_data_list = list()
        for index in indexes:
            if index.isValid() and index.column() == 0:
                db_data = self.cache.getPOIAtIndex(index.row())
                mime_data_list.append(db_data)
        mime_data.setText(json.dumps(mime_data_list, indent=2))
        return mime_data

    def keyPressEvent(self, e):
        pass
        # if e == Qt.QKeySequence.Copy:
        #    index = self.currentIndex()


class StyledItemDelegatePOI(QStyledItemDelegate):
    poi_edit_changed = Signal()

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
        data = self.cache.getPOIAtIndex(index.row())
        if data and editor.toPlainText() != index.data():
            self.cache.setPOIItemInfoText(data["destination_id"], editor.toPlainText())
            super(StyledItemDelegatePOI, self).setModelData(editor, model, index)
            self.poi_edit_changed.emit()
        else:
            super(StyledItemDelegatePOI, self).setModelData(editor, model, index)
