###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#                                                                         #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import os
import sys
import logging

class BasePath:
    """
        Base path for the resource access

        see: https://pyinstaller.org/en/stable/runtime-information.html
    """
    base_path = None
    def __init__(self):
        self.base_path = None

    @property
    def path(self)->str:
        if self.base_path is None:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                self.base_path = getattr(sys, '_MEIPASS', os.getcwd())
                logging.info("Running in a PyInstaller bundle.")
            else:
                self.base_path = os.getcwd()
        return self.base_path

sys_base_Path = BasePath()

def resourcePath(relative_path)->str:
    """
        Get absolute path to resource, works for dev and for PyInstaller
    Args:
        relative_path:

    Returns:
        str: full path
    """
    base_path = os.path.join(sys_base_Path.path, relative_path)
    if not os.path.exists(base_path):
        logging.info("Resource path not exists: {}.".format(base_path))
    return base_path


def resourcePathExists(relative_path)->bool:
    """
        Checks if the absolute path to resource, works for dev and for PyInstaller
    Args:
        relative_path:

    Returns:
        bool: True if the file exists else False
    """
    base_path = os.path.join(sys_base_Path.path, relative_path)
    return os.path.exists(base_path)
