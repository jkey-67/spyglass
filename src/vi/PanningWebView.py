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

from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import QApplication, qApp
from PyQt5.QtGui import *
from PyQt5 import QtCore

from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtCore import QEvent, Qt
import webbrowser
class WebEnginePage(QWebEnginePage):
    linkClicked = QtCore.pyqtSignal(QtCore.QUrl)
    def acceptNavigationRequest(self, url:QtCore.QUrl, nav_type, isMainFrame):
        if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
            self.linkClicked.emit(url)
            return False
        elif nav_type == QWebEnginePage.NavigationTypeTyped:
            return True
        elif nav_type == QWebEnginePage.NavigationTypeReload:
            return False
        elif nav_type == QWebEnginePage.NavigationTypeRedirect:
            return False
        else:
            return False

    def javaScriptConsoleMessage(self, QWebEnginePage_JavaScriptConsoleMessageLevel, p_str, p_int, p_str_1):
        return

class PanningWebView(QWebEngineView):
    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.pressed = False
        self.scrolling = False
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        profile = QWebEngineProfile(self)
        self.wepPage = WebEnginePage(profile, self)
        self.setPage(self.wepPage)
        self.page().setBackgroundColor(Qt.transparent)
        self.setAutoFillBackground(False)
        qApp.installEventFilter(self)

    def scrollPosition(self) -> QPointF:
        return self.page().scrollPosition()

    def setScrollPosition(self, pos: QPoint):
        if(  ( pos != None ) and ( pos != self.scrollPosition())):
            cnt_size = self.page().contentsSize()
            cnt_fac = self.page().zoomFactor()
            self.page().runJavaScript("window.scrollTo({0}, {1})".format(pos.x()/cnt_fac, pos.y()/cnt_fac))

    #event filter to split mouse messages
    def eventFilter(self, source, event) -> bool:
        try:
            if ((source.parent() == self) and (event.type() == QEvent.MouseButtonPress)):
                return self.mousePressEvent(event)
            if ((source.parent() == self) and (event.type() == QEvent.MouseMove)):
                return self.mouseMoveEvent(event)
            if ((source.parent() == self) and (event.type() == QEvent.MouseButtonRelease)):
                return self.mouseReleaseEvent(event)
            return False
        except:
            return False

    def mousePressEvent(self, mouseEvent:QMouseEvent) -> bool:
        pos = mouseEvent.pos()
        if self.pointInScroller(pos, QtCore.Qt.Vertical) or self.pointInScroller(pos, QtCore.Qt.Horizontal):
            return False
        else:
            if not self.pressed and not self.scrolling and mouseEvent.modifiers() == QtCore.Qt.NoModifier:
                if mouseEvent.buttons() == QtCore.Qt.LeftButton:
                    self.pressed = True
                    self.scrolling = False
                    self.handIsClosed = False
                    qApp.setOverrideCursor(QtCore.Qt.OpenHandCursor)
                    self.scrollMousePress = self.scrollPosition()
                    self.positionMousePress = mouseEvent.pos()
                    return True
        return False

    def mouseReleaseEvent(self, mouseEvent:QMouseEvent) -> bool:
        if self.scrolling:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            self.positionMousePress = None
            qApp.restoreOverrideCursor()
            return True

        if self.pressed:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            qApp.restoreOverrideCursor()
            return True
        return False

    def mouseMoveEvent(self, mouseEvent:QMouseEvent) -> bool:
            if self.scrolling:
                if not self.handIsClosed:
                    QApplication.restoreOverrideCursor()
                    QApplication.setOverrideCursor(QtCore.Qt.ClosedHandCursor)
                    self.handIsClosed = True
                if (self.scrollMousePress != None):
                    delta = mouseEvent.pos() - self.positionMousePress
                    self.setScrollPosition(self.scrollMousePress - delta)
                return True
            if self.pressed:
                self.pressed = False
                self.scrolling = True
                return True
            return False

    def pointInScroller(self, position, orientation):
        child = super().children()
        rcPage = self.page().contentsSize()
        rcCli = super().childrenRect()
        if (rcCli.width()<rcPage.width()):
            rcCli.setWidth(rcCli.width() - 16)
        if ( rcCli.height() < rcPage.height()):
            rcCli.setHeight(rcCli.height()-16)
        return not rcCli.contains(position)
