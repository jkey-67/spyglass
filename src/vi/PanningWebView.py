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
import logging

class PanningWebView(QWebEngineView):
    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.pressed = False
        self.scrolling = False
        self.ignored = []
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        self.page().setBackgroundColor(Qt.transparent)
        self.setAutoFillBackground(False)
        qApp.installEventFilter(self)

    def scrollPosition(self) -> QPointF:
        logging.critical("scrollPosition from page {0}".format(self.page().scrollPosition()))
        return self.page().scrollPosition()

    def setScrollPosition(self, pos: QPoint):
        if(  ( pos != None ) and ( pos != self.scrollPosition())):
            cnt_size = self.page().contentsSize()
            cnt_fac = self.page().zoomFactor()
            self.page().runJavaScript("window.scrollTo({0}, {1})".format(pos.x()/cnt_fac, pos.y()/cnt_fac))
            logging.critical("window.scrollTo({0},{1}, size {2} zoom {3})".format(pos.x(), pos.y(),cnt_size,cnt_fac))

    #event filter to split mouse messages
    def eventFilter(self, source, event) -> bool:
        if ((source.parent() == self) and (event.type() == QEvent.MouseButtonPress)):
            return self.mousePressEvent(event)
        if ((source.parent() == self) and (event.type() == QEvent.MouseMove)):
            return self.mouseMoveEvent(event)
        if ((source.parent() == self) and (event.type() == QEvent.MouseButtonRelease)):
            return self.mouseReleaseEvent(event)
        return False

    def mousePressEvent(self, mouseEvent:QMouseEvent) -> bool:
        pos = mouseEvent.pos()
        if self.pointInScroller(pos, QtCore.Qt.Vertical) or self.pointInScroller(pos, QtCore.Qt.Horizontal):
            return False
        else:
            if self.ignored.count(mouseEvent):
                self.ignored.remove(mouseEvent)
                return False

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
        if self.ignored.count(mouseEvent):
            self.ignored.remove(mouseEvent)
            return False

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
            #event1 = QMouseEvent(QEvent.MouseButtonPress, self.position, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
            #                     QtCore.Qt.NoModifier)
            #event2 = QMouseEvent(mouseEvent)
            #self.ignored.append(event1)
            #self.ignored.append(event2)
            #qApp.postEvent(self, event1)
            #qApp.postEvent(self, event2)
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
        rc = super().childrenRect()
        ch =self.childAt(position)
        return False
        # rect = self.page().scrollPosition()scrollBarGeometry(orientation)
        leftTop = self.mapToGlobal(QtCore.QPoint(rect.left(), rect.top()))
        rightBottom = self.mapToGlobal(QtCore.QPoint(rect.right(), rect.bottom()))
        globalRect = QtCore.QRect(leftTop.x(), leftTop.y(), rightBottom.x(), rightBottom.y())
        return globalRect.contains(self.mapToGlobal(position))
