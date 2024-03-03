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

from PySide6 import QtGui
from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from vi.evegate import checkTheraConnections


class TableModelThera(QAbstractTableModel):
    def __init__(self, system_name="V-F6DQ", parent=None):
        super(TableModelThera, self).__init__(parent)
        self.system_name = system_name
        self.thera_data = checkTheraConnections(system_name)
        self.model_display_list = [
            # {"created_at": ["created_at"]},
            # {"Created by ID": ["created_by_id"]},
            # {"Created by name": ["created_by_name"]},
            # {"updated_at": ["updated_at"]},
            # {"updated_by_id": ["updated_by_id"]},
            # {"completed_at": ["completed_at"]},
            # {"completed_by_id": ["completed_by_id"]},
            # {"completed_by_name": ["completed_by_name"]},
            # {"completed": ["completed"]},
            {"Sig In": ["in_signature"]},
            {"Sig Out": ["out_signature"]},
            {"Jumps": ["jumps"]},
            {"Region": ["in_region_name"]},
            {"System": ["in_system_name"]},
            {"Estimated EOL": ["expires_at"]},
            # {"wh_exits_outward": ["wh_exits_outward"]},
            # {"wh_type": ["wh_type"]},
            {"Max ship size": ["max_ship_size"]},
            {"Remaining hours": ["remaining_hours"]},
            # {"signature_type":  ["signature_type"]},
            # {"out_system_id": ["out_system_id"]},
            {"out_system_name":  ["out_system_name"]},
            # {"in_system_id":  ["in_system_id"]},
            # {"in_system_class":  ["in_system_class"]},
            {"ID": ["id"]},
            {"Comment": ["comment"]}
        ]

    def updateData(self, system_name=None):
        if system_name:
            self.system_name = system_name
        self.beginResetModel()
        self.thera_data = checkTheraConnections(self.system_name)
        self.endResetModel()

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return len(self.thera_data)

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return len(self.model_display_list)

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> Qt.ItemFlags:
        return Qt.ItemFlag.ItemIsEnabled

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        if role == Qt.DisplayRole:
            sel_item = self.thera_data[index.row()]
            sel_item_dict = self.model_display_list[index.column()]
            sel_item_key = list(self.model_display_list[index.column()].keys())[0]
            for value_list_txt in sel_item_dict[sel_item_key]:
                if value_list_txt in sel_item:
                    sel_item = sel_item[value_list_txt]
            return sel_item

        elif role == Qt.ForegroundRole:
            sel_item = self.thera_data[index.row()]
            if index.column() == 0:
                if sel_item["remaining_hours"] > 2:
                    return QtGui.QColor(0, 198, 0)
                else:
                    return QtGui.QColor(198, 0, 0)
            elif index.column() == 1:
                if sel_item["remaining_hours"] > 2:
                    return QtGui.QColor(0, 198, 0)
                else:
                    return QtGui.QColor(198, 0, 0)
            else:
                return None
        return None

    def index(self, row: int, column: int, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> QModelIndex:
        return self.createIndex(row, column, None)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return list(self.model_display_list[section].keys())[0]
        return None
