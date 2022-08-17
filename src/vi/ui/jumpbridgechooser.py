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
from PySide6 import QtWidgets
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtCore import Signal as pyqtSignal
from vi.resources import resourcePath
from vi.ui import Ui_JumpbridgeChooser
from vi import evegate


class JumpbridgeChooser(QtWidgets.QDialog):
    set_jumpbridge_url = pyqtSignal(str)

    def __init__(self, parent, url):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_JumpbridgeChooser()
        self.ui.setupUi(self)
        self.ui.saveButton.clicked.connect(self.savePath)
        self.ui.cancelButton.clicked.connect(self.cancelGenerateJumpBridge)
        self.ui.fileChooser.clicked.connect(self.choosePath)
        self.ui.generateJumpBridgeButton.clicked.connect(self.generateJumpBridge)
        self.ui.urlField.setText(url)
        # loading format explanation from textfile
        with open(resourcePath(os.path.join("docs", "jumpbridgeformat.txt"))) as f:
            self.ui.formatInfoField.setPlainText(f.read())
        self.ui.generateJumpBridgeProgress.hide()
        self.run_jb_generation = True

    def processUpdate(self, total, pos) -> bool:
        self.ui.generateJumpBridgeProgress.setMaximum(total)
        self.ui.generateJumpBridgeProgress.setValue(pos)
        QtWidgets.QApplication.processEvents()
        return self.run_jb_generation

    def generateJumpBridge(self):
        self.run_jb_generation = True
        self.ui.generateJumpBridgeProgress.show()
        gates = evegate.getAllJumpGates(evegate.esiCharName(), callback=self.processUpdate)
        evegate.writeGatestToFile(gates, str(self.ui.urlField.text()))
        self.ui.generateJumpBridgeProgress.hide()
        self.run_jb_generation = False

    def cancelGenerateJumpBridge(self):
        if self.run_jb_generation:
            self.run_jb_generation = False
        else:
            self.accept()

    def savePath(self):
        try:
            url = str(self.ui.urlField.text())
            self.set_jumpbridge_url.emit(url)
            self.accept()
        except Exception as e:
            QMessageBox.critical(None, "Finding jump bridge data failed", "Error: {0}".format(str(e)))

    def choosePath(self):
        path = QFileDialog.getOpenFileName(self, caption="Open JB Text File")[0]
        if os.path.exists(path):
            self.ui.rlField.setText(str(path))
