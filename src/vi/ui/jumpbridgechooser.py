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
from locale import format

from PySide6 import QtWidgets
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtCore import Signal as pyqtSignal
from vi.ui import Ui_JumpbridgeChooser
from vi import evegate
from vi.cache import Cache
from vi.universe import Universe

class JumpbridgeChooser(QtWidgets.QDialog):
    set_jumpbridge_url = pyqtSignal(str)
    update_jumpbridge = pyqtSignal()
    delete_jumpbridge = pyqtSignal()
    run_jb_generation = False

    def __init__(self, parent, url):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_JumpbridgeChooser()
        self.ui.setupUi(self)
        self.ui.saveButton.clicked.connect(self.exportFileName)
        self.ui.cancelButton.clicked.connect(self.cancelGenerateJumpBridge)
        self.ui.fileChooser.clicked.connect(self.importFileName)
        self.ui.generateJumpBridgeButton.clicked.connect(self.generateJumpBridge)
        self.ui.deleteAllJumpBridgeButton.clicked.connect(self.removeAllJumpbridges)
        self.ui.generateJumpBridgeButton.setEnabled(evegate.esiCharName() is not None)
        self.ui.urlField.setText(url)
        self.ui.generateJumpBridgeProgress.hide()
        self.run_jb_generation = False
        # self.setWindowFlags(Qt.Popup)
        self.fileDialog = QFileDialog(self)

    def done(self, arg__1: int) -> None:
        self.run_jb_generation = False
        QtWidgets.QDialog.done(self, arg__1)

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
        self.update_jumpbridge.emit()
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

    def exportFileName(self):
        save_path = QFileDialog.getSaveFileName(self,
                                                caption="Select JB Text File to export",
                                                dir=os.path.join(os.path.expanduser("~")))[0]
        if save_path == "":
            return

        query = "SELECT id_src, src, dst FROM jumpbridge"
        gates = Cache().con.execute(query, ()).fetchall()
        query = "SELECT id_dst, dst, src FROM jumpbridge"
        gates = gates + Cache().con.execute(query, ()).fetchall()

        def rgn_name_of_system(system_name):
            return Universe.regionNameFromSystemID(Universe.systemIdByName(system_name[1]))
        gates.sort(key=rgn_name_of_system)
        if gates is not None:
            try:
                with open(save_path, "w") as gf:
                    region_name = None
                    for gate in gates:

                        def get_structure_id(input_id):
                            if input_id is None:
                                structure_id = 0
                            else:
                                if input_id < 1000000000000:
                                    structure_id = 0
                                else:
                                    structure_id = input_id
                            return structure_id

                        region_name_curr = rgn_name_of_system(gate)
                        if region_name is not region_name_curr:
                            region_name = region_name_curr
                            gf.write("\n\n# {}\n\n".format(region_name_curr))
                        gf.write("{} {} --> {}".format(get_structure_id(gate[0]), gate[1], gate[2]) + "\n")

                    gf.close()
                logging.info("Export of all jumpbridge to file '{}' succeeded.".format(save_path))
            except Exception as e:
                logging.error(e)
                QMessageBox.critical(None, "Export  jump bridge data failed", "Error: {0}".format(str(e)))

    def importFileName(self):
        path = self.fileDialog.getOpenFileName(None,
                                               caption="Select JB Text File to export",
                                               dir=os.path.join(os.path.expanduser("~")))[0]
        if str(path) != "":
            self.ui.urlField.setText(str(path))

    def removeAllJumpbridges(self):
        self.delete_jumpbridge.emit()
        QtWidgets.QApplication.processEvents()
