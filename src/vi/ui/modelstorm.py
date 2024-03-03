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

from typing import Union, Any

from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from vi.evegate import ESAPIListPublicObservationsRecords


class TableModelStorm(QAbstractTableModel):
    def __init__(self, parent=None):
        super(TableModelStorm, self).__init__(parent)
        self.model_data = ESAPIListPublicObservationsRecords()
        self.model_display_list = [
            {"Name": ["display_name"]},
            {"Category": ["observation_category"]},
            {"System": ["system_name"]},
            {"Age": ["hours_in_system"]},
            {"ID": ["id"]},
            {"Created": ["created_at"]},
        ]

    def updateData(self):
        self.beginResetModel()
        self.model_data = ESAPIListPublicObservationsRecords()
        self.endResetModel()

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return len(self.model_data)

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return len(self.model_display_list)

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlags:
        return Qt.ItemFlag.ItemIsEnabled

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        if role == Qt.DisplayRole:
            sel_item = self.model_data[index.row()]
            sel_item_dict = self.model_display_list[index.column()]
            sel_item_key = list(self.model_display_list[index.column()].keys())[0]
            for value_list_txt in sel_item_dict[sel_item_key]:
                if value_list_txt in sel_item:
                    sel_item = sel_item[value_list_txt]
            return sel_item

        return None

    def index(self, row: int, column: int, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> QModelIndex:
        return self.createIndex(row, column, None)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return list(self.model_display_list[section].keys())[0]
        return None
