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
    def __init__(self, system_name="V-F6DQ", parent=None):
        self.model_display_list = [
            # {"Out ID": ["id"]},
            {"Out Sig": ["signatureId"]},
            {"In ID": ["wormholeDestinationSignatureId"]},
            {"System": ["destinationSolarSystem", "name"]},
            {"Security": ["destinationSolarSystem", "security"]},
            {"Region": ["destinationSolarSystem", "region", "name"]},
            {"Jumps": ["jumps"]},
            # {"Status": ["status"]},
            # {"lys": ["lightyears"]},
            # {"Destination Constellation ID": ["destinationSolarSystem", "constellationID"]},
            # {"Destination Region ID": ["destinationSolarSystem", "regionId"]},
            # {"Out Type": ["type"]},
            # {"Mass": ["wormholeMass"]},
            # {"EOL": ["wormholeEol"]},
            {"Estimated EOL": ["wormholeEstimatedEol"]}
            # {"Created": ["createdAt"]},
            # {"Updated": ["updatedAt"]},
            # {"Deleted": ["deletedAt"]},
            # {"Created by": ["createdBy"]},
            # {"Created by ID": ["createdById"]},
            # {"Deleted": ["deletedBy"]},
            # {"In Type": ["wormholeSourceWormholeTypeId"]},
            # {"Out Type": ["wormholeDestinationWormholeTypeId"]},
            # {"System ID": ["solarSystemId"]},
            # {"wormholeDestinationSolarSystemId": ["wormholeDestinationSolarSystemId"]},
            # {"Source WH Type": ["sourceWormholeType"]},
            # {"Source WH ID": ["sourceWormholeType", "id"]},
            # {"Source WH Name": ["sourceWormholeType", "name"]},
            # {"": ["sourceWormholeType", "src"]},
            # {"": ["sourceWormholeType", "dest"]},
            # {"": ["sourceWormholeType", "lifetime"]},
            # {"": ["sourceWormholeType", "jumpMass"]},
            # {"": ["sourceWormholeType", "maxMass"]},
            # {"": ["destinationWormholeType", "id"]},
            # {"": ["destinationWormholeType", "name"]},
            # {"": ["destinationWormholeType", "src"]},
            # {"": ["destinationWormholeType", "dest"]},
            # {"": ["destinationWormholeType", "lifetime"]},
            # {"": ["destinationWormholeType", "jumpMass"]},
            # {"": ["destinationWormholeType", "maxMass"]},
            # {"Source ID": ["sourceSolarSystem", "id"]},
            # {"Source Name": ["sourceSolarSystem", "name"]},
            # {"Source Name": ["sourceSolarSystem", "constellationID"]},
            # {"Source Security": ["sourceSolarSystem", "security"]},
            # {"Source Region ID": ["sourceSolarSystem", "regionId"]},
            # {"Source Region ID": ["sourceSolarSystem", "region", "id"]},
            # {"Source Region Name": ["sourceSolarSystem", "region", "name"]},
            # {"Destination System ID": ["destinationSolarSystem", "id"]},
            # {"Destination ID": ["destinationSolarSystem", "region", "id"]},
            # {"Destination": ["destinationSolarSystem", "region", "name"]},
            # {"Route": ["jump_route"]}]


            #{"Out Sig": ["signatureId"]},
            #{"In Sig": ["wormholeDestinationSignatureId"]},
            #{"System": ["destinationSolarSystem", "name"]},
            #{"Region": ["destinationSolarSystem", "region", "name"]},
            #{"Security": ["destinationSolarSystem", "security"]}
        ]
        super(TableModelThera, self).__init__(parent)
        self.system_name = system_name
        self.thera_data = checkTheraConnections(system_name)

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

    def flags(self, index: Union[QModelIndex, QPersistentModelIndex]) -> PySide6.QtCore.Qt.ItemFlags:
        return QtCore.Qt.ItemFlag.ItemIsEnabled

    def data(self, index: Union[QModelIndex, QPersistentModelIndex], role: int = ...) -> Any:
        node = index.internalPointer()
        if role == PySide6.QtCore.Qt.DisplayRole:
            sel_item = self.thera_data[index.row()]
            sel_item_dict = self.model_display_list[index.column()]
            sel_item_key = list(self.model_display_list[index.column()].keys())[0]
            for value_list_txt in sel_item_dict[sel_item_key]:
                sel_item = sel_item[value_list_txt]
            return sel_item

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
                case 1:
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
            return list(self.model_display_list[section].keys())[0]
        return None
