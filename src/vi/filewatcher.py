###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################
import logging
import os
import stat
import time
import datetime
import threading

from PySide6 import QtCore
from PySide6.QtCore import Signal as pyqtSignal

"""
There is a problem with the QFIleWatcher on Windows and the log
files from EVE.
The first implementation (now FileWatcher_orig) works fine on Linux, but
on Windows it seems ther is something buffered. Only a file-operation on
the watched directory another event there, which tirggers the OS to
reread the files informations, trigger the QFileWatcher.
So here is a workaround implementation.
We use here also a QFileWatcher, only to the directory. It will notify it
if a new file was created. We watch only the newest (last 24h), not all!
"""


class FileWatcher(QtCore.QThread):

    file_change = pyqtSignal(str, bool)
    files_to_ignore = ["Fleet", "Alliance"]
    FILE_LOCK = threading.Lock()

    def __init__(self, path):
        QtCore.QThread.__init__(self)
        self.path = path
        self.files = {}
        self.updateWatchedFiles()
        self.fileWatcher = QtCore.QFileSystemWatcher()
        self.fileWatcher.directoryChanged.connect(self.directoryChanged)
        self.fileWatcher.addPath(path)
        self.active = True

    def directoryChanged(self, path_name):
        with FileWatcher.FILE_LOCK:
            self.updateWatchedFiles()

    def run(self):
        while self.active:
            try:
                time.sleep(0.5)
                if not self.active:
                    return
                with FileWatcher.FILE_LOCK:
                    for path, size_file in self.files.items():
                        path_stat = os.stat(path)
                        if not stat.S_ISREG(path_stat.st_mode):
                            continue
                        if size_file < path_stat.st_size:
                            logging.debug("Update file {}".format(path))
                            self.file_change.emit(path, False)
                        self.files[path] = path_stat.st_size
            except Exception as e:
                logging.critical(e)

    def quit(self):
        self.active = False
        QtCore.QThread.quit(self)

    def lastDowntime(self):
        """ Return the timestamp from the last downtime
        """
        target = datetime.datetime.utcnow()
        if target.hour < 11:
            target = target - datetime.timedelta(1)
        target = datetime.datetime(target.year, target.month, target.day, 11, 5, 0, 0)
        return target.timestamp()

    def updateWatchedFiles(self):
        """
        Updates the list of monitored file, all Fleet and Alliance chats and files with mdate, earlier then the last
        downtime, will be ignored by default.

        Returns:
            None: modifies the file member
        """
        now = time.time()
        path = self.path
        files_in_dir = {}
        last_downtime = self.lastDowntime()
        for f in os.listdir(path):
            try:
                full_path = os.path.join(path, f)
                path_stat = os.stat(full_path)
                if not stat.S_ISREG(path_stat.st_mode):
                    continue
                if path_stat.st_mtime < last_downtime:
                    logging.debug("Ignor file {}, files m-time is outdated.".format(f))
                    continue
                if [elem for elem in FileWatcher.files_to_ignore if (elem in f)]:
                    logging.debug("Ignor file {}, found black listed token in filename.".format(f))
                    continue
                files_in_dir[full_path] = self.files.get(full_path, 0)
            except Exception as e:
                logging.error(e)
        self.files = files_in_dir
