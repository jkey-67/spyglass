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

import logging
import os
import sys
import stat
import time
import threading

from PySide6 import QtCore
from PySide6.QtCore import Signal

from vi.evetime import lastDowntime

"""
There is a problem with the QFIleWatcher on Windows and the log
files from EVE.
The first implementation (now FileWatcher_orig) works fine on Linux, but
on Windows it seems there is something buffered. Only a file-operation on
the watched directory another event there, which triggers the OS to
reread the files information, trigger the QFileWatcher.
So here is a workaround implementation.
We use here also a QFileWatcher, only to the directory. It will notify it
if a new file was created. We watch only the newest (last 24h), not all!
"""


class FileWatcher(QtCore.QThread):

    file_change = Signal(str, bool)
    files_to_ignore = ["Fleet", "Alliance", "Corp"]
    FILE_LOCK = threading.Lock()

    def __init__(self, path):
        QtCore.QThread.__init__(self)
        self.path = path
        self.files = {}  # path -> {"size": int, "mtime": float}
        self.fileWatcher = QtCore.QFileSystemWatcher(self)
        self.fileWatcher.directoryChanged.connect(self.directoryChanged)
        self.fileWatcher.fileChanged.connect(self.fileChanged)
        if os.path.isdir(path):
            self.fileWatcher.addPath(path)
        else:
            logging.warning("Log directory '%s' does not exist yet. Watching will start once it is created.", path)
        self.updateWatchedFiles()
        self.active = sys.platform.startswith("win32")

    def fileChanged(self, file_name):
        if os.path.exists(file_name):
            changed = False
            with FileWatcher.FILE_LOCK:
                try:
                    path_stat = os.stat(file_name)
                except (OSError,):
                    return
                self.updateWatchedFiles()
                if not stat.S_ISREG(path_stat.st_mode):
                    return
                prev = self.files.get(file_name, {"size": 0, "mtime": 0})
                if (
                    prev["size"] != path_stat.st_size
                    or prev["mtime"] != path_stat.st_mtime
                ):
                    logging.debug("Update file {}".format(file_name))
                    self.files[file_name] = {
                        "size": path_stat.st_size,
                        "mtime": path_stat.st_mtime,
                    }
                    changed = True
            if changed:
                self.file_change.emit(file_name, False)

    def directoryChanged(self, path_name):
        with FileWatcher.FILE_LOCK:
            self.updateWatchedFiles(path_name)

    def run(self):
        """Poll watched files so file growth is detected even without OS events.

        Returns:
            None
        """
        while self.active:
            try:
                time.sleep(0.5)
                if not self.active:
                    return
                with FileWatcher.FILE_LOCK:
                    self.updateWatchedFiles()
                    for path, metadata in self.files.items():
                        try:
                            path_stat = os.stat(path)
                        except (OSError,):
                            continue
                        if not stat.S_ISREG(path_stat.st_mode):
                            continue
                        if metadata["size"] != path_stat.st_size or metadata["mtime"] != path_stat.st_mtime:
                            logging.debug("Update file {}".format(path))
                            self.file_change.emit(path, False)
                        self.files[path] = { "size": path_stat.st_size, "mtime": path_stat.st_mtime, }
            except (Exception,) as e:
                logging.critical(e)

    def quit(self):
        self.active = False
        QtCore.QThread.quit(self)

    def updateWatchedFiles(self, path_name=None):
        """Refresh the list of files to monitor.

        Spyglass can start before the EVE client creates the log folder, so a missing
        directory is silently ignored. Fleet/Alliance chats and files older than last
        downtime continue to be excluded.

        Args:
            path_name: Optional override to watch a different directory this call.

        Returns:
            None
        """
        path = path_name if path_name else self.path
        if not os.path.isdir(path):
            return
        last_downtime = lastDowntime()
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
                self.addMonitorFile(
                    full_path,
                    initial_size=path_stat.st_size,
                    initial_mtime=path_stat.st_mtime,
                )

            except (Exception,) as e:
                logging.error(e)

    def addMonitorFile(self, filename, initial_size=None, initial_mtime=None):
        """Register a file for monitoring and seed its current size.

        Args:
            filename: Full path to the log file.
            initial_size: Optional byte size to seed; defaults to the current size.
            initial_mtime: Optional mtime to seed; defaults to the current mtime.

        Returns:
            None
        """
        if filename in self.files:
            return
        if initial_size is None or initial_mtime is None:
            try:
                path_stat = os.stat(filename)
                initial_size = path_stat.st_size
                initial_mtime = path_stat.st_mtime
            except (OSError,):
                initial_size = 0
                initial_mtime = 0
        self.files[filename] = {"size": initial_size, "mtime": initial_mtime}
        if os.path.exists(filename):
            self.fileWatcher.addPath(filename)
