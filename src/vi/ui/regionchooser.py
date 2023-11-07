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
import requests

from vi.cache import Cache
from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtWidgets import QMessageBox
from vi.ui import Ui_RegionChooser
from vi import evegate, dotlan
from vi.resources import resourcePathExists


class RegionChooser(QtWidgets.QDialog):
    new_region_chosen = pyqtSignal(str)

    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_RegionChooser()
        self.ui.setupUi(self)

        self.strList = QtWidgets.QCompleter(
            ["{}".format(name) for key, name in evegate.esiUniverseNames(evegate.esiUniverseGetAllRegions()).items()],
            parent=self)

        self.strList.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.ui.regionNameField.setCompleter(self.strList)
        self.ui.saveButton.clicked.connect(self.saveClicked)
        cache = Cache()
        region_name = cache.getFromCache("region_name")
        if not region_name:
            region_name = u"Providence"
        self.ui.regionNameField.setText(region_name)

    def saveClicked(self):
        text = str(self.ui.regionNameField.text())
        text = dotlan.convertRegionName(text)
        self.ui.regionNameField.setText(text)
        try:
            url = dotlan.Map.DOTLAN_BASIC_URL.format(text)
            content = requests.get(url).text
            if u"not found" in content:
                try:
                    correct = resourcePathExists(os.path.join("vi", "ui", "res", "mapdata", "{0}.svg".format(text)))
                except Exception as e:
                    logging.error(e)
                    correct = False
                if not correct:
                    QMessageBox.warning(self, u"No such region!", u"I can't find a region called '{0}'".format(text))
            else:
                correct = True
        except Exception as e:
            QMessageBox.critical(self, u"Something went wrong!", u"Error while testing existing '{0}'".format(str(e)))
            logging.error(e)
            correct = False
        if correct:
            Cache().putIntoCache("region_name", text, 60 * 60 * 24 * 365)
            self.accept()
            self.new_region_chosen.emit(text)


