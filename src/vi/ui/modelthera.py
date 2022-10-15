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

from PySide6 import QtCore
from PySide6.QtCore import QAbstractTableModel
from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from vi.evegate import checkTheraConnections

import PySide6.QtCore


class TableModelThera(QAbstractTableModel):
    def __init__(self, parent=None):
        super(TableModelThera, self).__init__(parent)
        self.thera_data = checkTheraConnections("V-F6DQ")

    def rowCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return len(self.thera_data)

    def columnCount(self, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> int:
        return 9

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> PySide6.QtCore.Qt.ItemFlags:
        return QtCore.Qt.ItemFlag.ItemIsEnabled

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        node = index.internalPointer()
        if role == PySide6.QtCore.Qt.DisplayRole:
            sel_item = self.thera_data[index.row()]
            source_system = sel_item["sourceSolarSystem"]
            destination_system = sel_item["destinationSolarSystem"]
            match index.column():
                case 0:
                    return sel_item["signatureId"]
                case 1:
                    return sel_item["wormholeDestinationSignatureId"]
                case 2:
                    return destination_system["name"]
                case 3:
                    return destination_system["region"]["name"]
                case 4:
                    return destination_system["security"]
                case 5:
                    return sel_item["jumps"]
                case 6:
                    return sel_item["wormholeMass"]
                case 7:
                    return sel_item["wormholeEol"]
                case 8:
                    return sel_item["wormholeEstimatedEol"]
                case _:
                    return None
        elif role == PySide6.QtCore.Qt.ForegroundRole:
            sel_item = self.thera_data[index.row()]
            source_system = sel_item["sourceSolarSystem"]
            destination_system = sel_item["destinationSolarSystem"]
            match index.column():
                case 0:
                    if sel_item["wormholeEol"] == "stable":
                        return PySide6.QtGui.QColor(0, 198, 0)
                    elif sel_item["wormholeEol"] == "critical":
                        return PySide6.QtGui.QColor(198, 0, 0)
                    else:
                        return None
                case _:
                    return None
        return None

    def index(self, row: int, column: int, parent: Union[QModelIndex, QPersistentModelIndex] = ...) -> QModelIndex:
        return self.createIndex(row, column, None)

    def headerData(self, section: int, orientation: PySide6.QtCore.Qt.Orientation, role: int = ...) -> Any:
        if role != PySide6.QtCore.Qt.DisplayRole:
            return None
        if orientation == PySide6.QtCore.Qt.Horizontal:
            match section:
                case 0:
                    return "Out Sig"
                case 1:
                    return "In Sig"
                case 2:
                    return "System"
                case 3:
                    return "Region"
                case 4:
                    return "Security"
                case 5:
                    return "Jumps"
                case 6:
                    return "Mass"
                case 7:
                    return "Eol"
                case 8:
                    return "Eol Date"
        return None
