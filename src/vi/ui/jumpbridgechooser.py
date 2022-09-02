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
import logging
import os
from PySide6 import QtWidgets
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtCore import Signal as pyqtSignal
from vi.ui import Ui_JumpbridgeChooser
from vi import evegate
from vi.cache import Cache


class JumpbridgeChooser(QtWidgets.QDialog):
    set_jumpbridge_url = pyqtSignal(str)

    def __init__(self, parent, url):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_JumpbridgeChooser()
        self.ui.setupUi(self)
        self.ui.saveButton.clicked.connect(self.savePath)
        self.ui.cancelButton.clicked.connect(self.cancelGenerateJumpBridge)
        self.ui.fileChooser.clicked.connect(self.choosePathSave)
        self.ui.generateJumpBridgeButton.clicked.connect(self.generateJumpBridge)
        self.ui.generateJumpBridgeButton.setEnabled(evegate.esiCharName() is not None)
        self.ui.urlField.setText(url)
        self.ui.saveButton.setEnabled(url != "")
        self.ui.urlField.editingFinished.connect(
            lambda:
                self.ui.saveButton.setEnabled(self.ui.urlField.text() != "")
        )
        self.ui.generateJumpBridgeProgress.hide()
        self.run_jb_generation = False

    def processUpdate(self, total, pos) -> bool:
        """
        progress indicator for the jumpbridge update
        Args:
            total: total count
            pos:  current

        Returns:
            true to continue, false to break

        """
        self.ui.generateJumpBridgeProgress.setMaximum(total)
        self.ui.generateJumpBridgeProgress.setValue(pos)
        QtWidgets.QApplication.processEvents()
        return self.run_jb_generation

    def generateJumpBridge(self):
        self.run_jb_generation = True
        self.ui.generateJumpBridgeProgress.show()
        evegate.getAllJumpGates(evegate.esiCharName(), callback=self.processUpdate)
        self.ui.generateJumpBridgeProgress.hide()
        self.run_jb_generation = False

    def signalURLChange(self):
        url = str(self.ui.urlField.text())
        self.set_jumpbridge_url.emit(url)

    def cancelGenerateJumpBridge(self):
        if self.run_jb_generation:
            self.run_jb_generation = False
        else:
            self.signalURLChange()
            self.accept()

    def savePath(self):
        save_path = QFileDialog.getSaveFileName(self,
                                           caption="Select JB Text File to export",
                                           dir=os.path.join(os.path.expanduser("~")))[0]
        if save_path == "":
            return

        query = "SELECT src, dst FROM jumpbridge"
        gates = Cache().con.execute(query, ()).fetchall()

        if gates is not None:
            try:
                with open(save_path, "w") as gf:
                    for gate in gates:
                        gf.write("{} » {}".format(gate[0], gate[1])+"\n")
                    gf.close()
                logging.info("Export of all jumpbridge to file '{}' succeeded.".format(save_path))
            except Exception as e:
                logging.error(e)
                QMessageBox.critical(None, "Export  jump bridge data failed", "Error: {0}".format(str(e)))

    def choosePathSave(self):
        path = QFileDialog.getSaveFileName(self,
                                           caption="Select JB Text File to export",
                                           dir=os.path.join(os.path.expanduser("~")))[0]
        if str(path) != "":
            self.ui.urlField.setText(str(path))
            self.ui.saveButton.setEnabled(self.ui.urlField.text() != "")
