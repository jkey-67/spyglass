#!/usr/bin/env python
###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#  																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#  																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#  																		  #
#  																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import sys
import os
import logging
import traceback
import datetime
from logging.handlers import RotatingFileHandler
from PySide6 import QtGui, QtWidgets
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtSql import QSqlDatabase
from PySide6.QtCore import Qt

from vi.version import VERSION, SNAPSHOT
from vi.ui import viui, systemtray
from vi.cache import cache
from vi.ui.styles import Styles
from vi.resources import resourcePath
from vi.cache.cache import Cache
from vi.zkillboard import Zkillmonitor


def exceptHook(exception_type, exception_value, traceback_object):
    """
        Global function to catch unhandled exceptions.
    """
    try:
        logging.critical("-- Unhandled Exception ---------------------------------------------------------------------")
        logging.critical(''.join(traceback.format_tb(traceback_object)))
        logging.critical('{0}: {1}'.format(exception_type, exception_value))
        logging.critical("--------------------------------------------------------------------------------------------")
    except (Exception,):
        pass


sys.excepthook = exceptHook
backGroundColor = "#c6d9ec"


class Application(QApplication):
    def __init__(self, args):
        super(Application, self).__init__(args)
        pixmap = QtGui.QPixmap(resourcePath("vi/ui/res/logo_splash.png"))
        if SNAPSHOT:
            painter = QtGui.QPainter()
            painter.begin(pixmap)
            font = painter.font()
            font.setPixelSize(60)
            font.setBold(True)
            painter.save()
            painter.setPen(Qt.red)
            painter.setFont(font)
            painter.rotate(30.0)
            painter.drawText(200, 0, "Snapshot Version")
            painter.restore()
            painter.end()
        self.splash = QtWidgets.QSplashScreen(pixmap)
        self.splash.show()
        QApplication.processEvents()

        def change_splash_text(txt):
            # logging.info(txt)
            if self.splash and len(txt):
                self.splash.showMessage("   {}".format(txt), Qt.AlignLeft, QtGui.QColor(0x808000))

        chat_log_directory = ""
        if len(sys.argv) > 1:
            chat_log_directory = sys.argv[1]
        change_splash_text("fetch path and os")
        if not os.path.exists(chat_log_directory):
            if sys.platform.startswith("darwin"):
                change_splash_text("fetch path anf os, darwin detected")
                chat_log_directory = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "logs", "Chatlogs")
                if not os.path.exists(chat_log_directory):
                    chat_log_directory = os.path.join(os.path.expanduser("~"), "Library", "Application Support",
                                                      "Eve Online", "p_drive", "User", "My Documents", "EVE",
                                                      "logs", "Chatlogs")
            elif sys.platform.startswith("linux"):
                change_splash_text("fetch path anf os, linux detected")
                chat_log_directory = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "logs", "Chatlogs")
            elif sys.platform.startswith("win32") or sys.platform.startswith("cygwin"):
                change_splash_text("fetch path anf os, windows detected")
                import ctypes.wintypes
                buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(0, 0x05, 0, 0, buf)
                documents_path = buf.value
                from os.path import expanduser
                chat_log_directory = os.path.join(documents_path, "EVE", "logs", "Chatlogs")
                # Now I need to just make sure... Some old pcs could still be on XP
                if not os.path.exists(chat_log_directory):
                    chat_log_directory = os.path.join(os.path.expanduser("~"), "My Documents", "EVE",
                                                      "logs", "Chatlogs")

        if not os.path.exists(chat_log_directory):
            chat_log_directory = QtWidgets.QFileDialog.getExistingDirectory(
                None,
                caption="Select EVE Online chat  logfiles directory", dir=chat_log_directory)

        if not os.path.exists(chat_log_directory):
            # None of the paths for logs exist, bailing out
            QMessageBox.critical(None, "No path to Logs", "Unable to find the log files at:\n\n" + chat_log_directory +
                                 "\n\nThe Spyglass Application will be terminated.", QMessageBox.Close)
            sys.exit(1)

        change_splash_text("setting local directory for cache and logging")

        spyglass_dir = os.path.join(os.path.dirname(os.path.dirname(chat_log_directory)), "spyglass")
        Zkillmonitor.MONITORING_PATH = os.path.join(chat_log_directory,
                                                    datetime.datetime.strftime(
                                                        datetime.datetime.now(datetime.UTC),
                                                        "zKillboard_daily_logfile_%Y%m%d.txt"))

        if not os.path.exists(spyglass_dir):
            os.mkdir(spyglass_dir)
        cache.Cache.PATH_TO_CACHE = os.path.join(spyglass_dir, "cache-2.sqlite3")
        self.con = QSqlDatabase.addDatabase("QSQLITE")
        self.con.setDatabaseName(cache.Cache.PATH_TO_CACHE)
        self.con.open()

        spyglass_log_directory = os.path.join(spyglass_dir, "logs")
        if not os.path.exists(spyglass_log_directory):
            os.mkdir(spyglass_log_directory)

        spyglass_cache = Cache()
        log_level = spyglass_cache.getFromCache("logging_level")
        if not log_level:
            log_level = logging.INFO
        if SNAPSHOT:
            log_level = logging.DEBUG  # For Testing
        spyglass_cache.clearOutdatedPlayerNames()
        back_ground_color = spyglass_cache.getFromCache("background_color")

        if back_ground_color:
            self.setStyleSheet("background-color: %s;" % back_ground_color)
        css = Styles.getStyle()
        self.setStyleSheet(css)
        del css

        root_logger = logging.getLogger()
        root_logger.setLevel(level=log_level)
        # Setup logging for console and rotated log files
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter('"%(asctime)s - "/%(pathname)s:%(lineno)s)" : %(message)s'))

        log_filename = spyglass_log_directory + "/output.log"
        file_handler = RotatingFileHandler(maxBytes=(1048576 * 5), backupCount=7, filename=log_filename, mode='a')
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)9s [%(filename)s:%(lineno)s] - %(message)s"))
        root_logger.addHandler(stream_handler)
        root_logger.addHandler(file_handler)

        logging.info("================================================================================================")
        logging.info("Spyglass %s starting up", VERSION)
        logging.info("Looking for chat logs at: {0}".format(chat_log_directory))
        logging.info("Cache maintained here: {0}".format(cache.Cache.PATH_TO_CACHE))
        logging.info("Writing logs to: {0}".format(spyglass_log_directory))
        logging.info("================================================================================================")
        tray_icon = systemtray.TrayIcon(self)
        tray_icon.show()

        change_splash_text("init main windows")
        QApplication.processEvents()
        self.mainWindow = viui.MainWindow(chat_log_directory, tray_icon, change_splash_text)
        self.splash.finish(self.mainWindow)
        self.mainWindow.show()
        self.mainWindow.raise_()

        logging.info("Initialisation completed =======================================================================")

    def __del__(self):
        logging.info("Spyglass terminated normal =====================================================================")


"""
    The main application
"""

if __name__ == "__main__":
    res = 0
    try:
        # os.environ["XDG_SESSION_TYPE"] = "wayland"
        # os.environ["QT_QPA_PLATFORM"] = "wayland"
        app = Application(sys.argv)
        res = app.exec()
        del app
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()

        info = "Traceback\n"
        while exc_tb:
            filename = exc_tb.tb_frame.f_code.co_filename
            line = exc_tb.tb_lineno
            info = "{}   File \"{}\", line {}\n".format(info, filename, line)
            exc_tb = exc_tb.tb_next

        logging.critical("Spyglass terminated abnormal : %s\n%s. ", e.__str__(), info)
        logging.info("================================================================================================")
    sys.exit(res)
