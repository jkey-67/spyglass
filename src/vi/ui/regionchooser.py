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

from vi.cache import Cache
from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6.QtCore import Signal as pyqtSignal
from vi.ui import Ui_RegionChooser
from vi.universe import Universe


class RegionChooser(QtWidgets.QDialog):
    new_region_chosen = pyqtSignal(str)

    def __init__(self, parent, region_name: str):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_RegionChooser()
        self.ui.setupUi(self)
        self.list_of_reagion_names = sorted([region["name"] for region in Universe.REGIONS])
        self.strList = QtWidgets.QCompleter(self.list_of_reagion_names, parent=self)
        self.strList.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.ui.regionNameField.addItems(self.list_of_reagion_names)
        self.ui.regionNameField.setCompleter(self.strList)
        self.ui.regionNameField.setCurrentText(region_name)
        self.ui.regionNameField.currentIndexChanged.connect(self.indexChanged)
        self.ui.saveButton.clicked.connect(self.saveClicked)

    def indexChanged(self, index: int):
        region_name = str(self.ui.regionNameField.currentText())
        if region_name in self.list_of_reagion_names:
            self.new_region_chosen.emit(region_name)

    def saveClicked(self):
        region_name = str(self.ui.regionNameField.currentText())
        if region_name in self.list_of_reagion_names:
            self.new_region_chosen.emit(region_name)
            self.accept()



