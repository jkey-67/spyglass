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

from PyQt5.QtWidgets import QApplication, qApp, QWidget
from PyQt5.QtGui import *
from PyQt5 import QtCore, QtSvg

from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtCore import Qt
import logging
import os

class PanningWebView(QWidget):
    webViewResized = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.zoom = 1.0
        self.setImgSize(QtCore.QSize(100,80))
        self.qsvg = None
        self.pressed = False
        self.scrolling = False
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scrollPos = QPointF(0.0, 0.0)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.qsvg = QtSvg.QSvgRenderer()
        self.qsvg.setAspectRatioMode(Qt.KeepAspectRatioByExpanding)
        self.qsvg.repaintNeeded.connect(self.update)


    def setContent(self, cnt, type):
        if not self.qsvg.load(cnt):
            logging.error("error during parse of svg data")
        self.setImgSize(self.qsvg.defaultSize())
        self.qsvg.setFramesPerSecond(0)
        self.qsvg.setAspectRatioMode(Qt.KeepAspectRatio)

    def setImgSize(self, newsize: QtCore.QSize):
        self.imgSize = newsize
        rcNew = self.imgSize*self.zoom
        rcNew.setWidth(self.imgSize.width() * self.zoom)
        rcNew.setHeight(self.imgSize.height() * self.zoom)

    def resizeEvent(self, event: QResizeEvent):
        self.webViewResized.emit()
        super().resizeEvent(event)

    def paintEvent(self, event):
        if self.qsvg:
            painter = QPainter(self)
            rect = QtCore.QRectF(-self.scrollPos.x(), -self.scrollPos.y(), self.qsvg.defaultSize().width()*self.zoom,self.qsvg.defaultSize().height()*self.zoom)
            self.qsvg.render(painter, rect)

    def setZoomFactor(self, zoom):
        if zoom > 8:
            zoom = 8
        elif zoom < 0.5:
            zoom = 0.5
        if self.zoom != zoom:
            self.zoom = zoom
            self.webViewResized.emit()
            if self.imgSize.isValid():
                self.setImgSize(self.imgSize)
            self.update()


    def zoomFactor(self):
        return self.zoom

    def scrollPosition(self) -> QPointF:
        return self.scrollPos

    def setScrollPosition(self, pos: QPoint):
        if self.scrollPos != pos:
            self.scrollPos = pos

            if self.scrollPos.x() > self.imgSize.width()*self.zoom-self.size().width():
                self.scrollPos.setX(self.imgSize.width()*self.zoom-self.size().width())
            if self.scrollPos.x() < -self.imgSize.width()*self.zoom/2:
                self.scrollPos.setX(-self.imgSize.width()*self.zoom/2)

            if self.scrollPos.y() > self.imgSize.height()*self.zoom-self.size().height():
                self.scrollPos.setY(self.imgSize.height()*self.zoom-self.size().height())
            if self.scrollPos.y() < -self.imgSize.height()*self.zoom/2:
                self.scrollPos.setY(-self.imgSize.height()*self.zoom/2)

            self.webViewResized.emit()
            self.update()

    def zoomIn(self,pos=None):
        if pos==None:
            self.setZoomFactor(self.zoomFactor() * 1.4)
        else:
            elemOri=self.mapPosFromPos(pos)
            self.setZoomFactor(self.zoom * 1.4)
            elemDelta =elemOri-self.mapPosFromPos(pos)
            self.scrollPos=self.scrollPos+elemDelta*self.zoom

    def zoomOut(self, pos=None):
        if pos == None:
            self.setZoomFactor(self.zoom*0.6)
        else:
            elem_ori = self.mapPosFromPos(pos)
            self.setZoomFactor(self.zoom*0.6)
            elem_delta = elem_ori - self.mapPosFromPos(pos)
            self.scrollPos = self.scrollPos+elem_delta*self.zoom

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() < 0:
            self.zoomIn(event.position())
        elif event.angleDelta().y() > 0:
            self.zoomOut(event.position())

    def mousePressEvent(self, mouseEvent:QMouseEvent):
        if not self.pressed and not self.scrolling and mouseEvent.modifiers() == QtCore.Qt.NoModifier:
            if mouseEvent.buttons() == QtCore.Qt.LeftButton:
                self.pressed = True
                self.scrolling = False
                self.handIsClosed = False
                qApp.setOverrideCursor(QtCore.Qt.OpenHandCursor)
                self.scrollMousePress = self.scrollPosition()
                self.positionMousePress = mouseEvent.pos()

    def mouseReleaseEvent(self, mouseEvent:QMouseEvent):
        if self.scrolling:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            self.positionMousePress = None
            qApp.restoreOverrideCursor()
            return

        if self.pressed:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            qApp.restoreOverrideCursor()
            return

    def hoveCheck(self,pos:QPoint)->bool:
        return False

    def doubleClicked(self,pos:QPoint)->bool:
        return False

    def mouseDoubleClickEvent(self, mouseEvent:QMouseEvent):
        self.doubleClicked(self.mapPosFromEvent(mouseEvent))

    def mapPosFromPos(self, pos:QPointF)->QPointF:
        return (pos + self.scrollPos) / self.zoom

    def mapPosFromPoint(self,mouseEvent:QPoint)->QPoint:
        return (mouseEvent + self.scrollPos) / self.zoom

    def mapPosFromEvent(self,mouseEvent:QMouseEvent)->QPointF:
        return (mouseEvent.pos() + self.scrollPos) / self.zoom

    def mouseMoveEvent(self, mouseEvent:QMouseEvent):
        if self.scrolling:
            if not self.handIsClosed:
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)
                self.handIsClosed = True
            if self.scrollMousePress != None:
                delta = mouseEvent.pos() - self.positionMousePress
                self.setScrollPosition(self.scrollMousePress - delta)
            return
        if self.pressed:
            self.pressed = False
            self.scrolling = True
            return
        if self.hoveCheck(self.mapPosFromEvent(mouseEvent)):
            QApplication.setOverrideCursor(QtCore.Qt.PointingHandCursor)
        else:
            QApplication.setOverrideCursor(QtCore.Qt.ArrowCursor)
        return

