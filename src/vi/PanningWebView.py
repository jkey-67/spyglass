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

from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QEvent, Qt


class PanningWebView(QWebEngineView):
    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.pressed = False
        self.scrolling = False
        self.ignored = []
        self.position = None
        self.scrollPos  = None
        self.offset = None
        self.offset_x = None
        self.offset_y = None
        self.handIsClosed = False
        self.page().setBackgroundColor(Qt.transparent)
        self.setAutoFillBackground(False)
        qApp.installEventFilter(self)

    def startUpdateScrollPositions(self):
        def set_x(val):
            self.offset_x = val
            if ((self.offset_x != None) and (self.offset_y != None)):
                self.offset = QtCore.QPoint(self.offset_x, self.offset_y)

        def set_y(val):
            self.offset_y = val
            if ((self.offset_x != None) and (self.offset_y != None)):
                self.offset = QtCore.QPoint(self.offset_x, self.offset_y)

        self.offset = None
        self.offset_x = None
        self.offset_y = None
        self.page().runJavaScript("window.scrollX", set_x)
        self.page().runJavaScript("window.scrollY", set_y)

    def scrollPosition(self) -> QPoint:
        return self.scrollPos

    def setScrollPosition(self, pos: QPoint):
        self.scrollPos = pos
        if ( self.scrollPos != None ):
            self.page().runJavaScript("window.scrollTo({0}, {1})".format(self.scrollPos.x(), self.scrollPos.y()))
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
                    self.position = mouseEvent.pos()
                    self.startUpdateScrollPositions()
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
                if (self.offset != None):
                    delta = mouseEvent.pos() - self.position
                    self.setScrollPosition(self.offset - delta)
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
