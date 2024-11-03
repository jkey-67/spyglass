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
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QWidget

from PySide6.QtGui import QPainter, QResizeEvent, QWheelEvent, QMouseEvent, QTransform
from PySide6.QtCore import QPoint, QPointF, Signal, QSizeF
from PySide6.QtCore import Qt, QEvent


class PanningWebView(QWidget):
    ZOOM_WHEEL = 0.4
    webViewIsScrolling = Signal(bool)
    webViewUpdateScrollbars = Signal()
    webViewNavigateForward = Signal()
    webViewNavigateBackward = Signal()
    webViewDoubleClicked = Signal(QPointF)

    def __init__(self, parent=None):
        super(PanningWebView, self).__init__(parent)
        self.content = None
        self.transform = QTransform()
        self.zoom = 1.0
        self.wheel_dir = 1.0
        self.imgSize = QSizeF(1024.0, 768.0)
        self.pressed = False
        self.scrolling = False
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scrollPos = QPointF(0.0, 0.0)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def setContent(self, cnt):
        if self.scrolling:
            return False
        self.content = cnt
        self.update()
        return True

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.webViewUpdateScrollbars.emit()

    def paintEvent(self, event):
        if self.content is None:
            return
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            self.transform.translate(-self.scrollPos.x(), -self.scrollPos.y())
            self.transform.scale(self.zoom, self.zoom)
            painter.setTransform(self.transform)
            self.content.renderMap(painter)
            self.transform.reset()
            self.transform.scale(2.0, 2.0)
            painter.setTransform(self.transform)
            self.content.renderLegend(painter)
            self.transform.reset()
        except (Exception,):
            pass

    def setZoomFactor(self, zoom: float):
        if zoom > 8.0:
            zoom = 8.0
        elif zoom < 0.125:
            zoom = 0.125
        if self.zoom != zoom:
            self.zoom = zoom
            self.webViewUpdateScrollbars.emit()
            self.update()

    def zoomFactor(self):
        return self.zoom

    def scrollPosition(self) -> QPointF:
        return self.scrollPos

    def setScrollPosition(self, pos: QPointF):
        if self.scrolling:
            return
        self._setScrollPosition(pos)

    def _setScrollPosition(self, pos: QPointF):
        if self.scrollPos != pos:
            self.scrollPos = pos
            self.webViewUpdateScrollbars.emit()
            self.update()

    def setZoomAndScrollPos(self, zoom, pos):
        if self.scrolling:
            return
        changed = False
        if zoom and self.zoom != zoom:
            if zoom > 8.0:
                zoom = 8.0
            elif zoom < 0.125:
                zoom = 0.125
            if self.zoom != zoom:
                self.zoom = zoom
                changed = changed or True
        if pos and self.scrollPos != pos:
            if self.scrollPos != pos:
                self.scrollPos = pos
                changed = changed or True
        if changed:
            self.webViewUpdateScrollbars.emit()
            self.update()

    def zoomIn(self, pos=None):
        if self.scrolling:
            return

        if pos is None:
            pos = QPointF(self.size().width()/2.0, self.size().height()/2.0)

        elem_ori = self.mapPosFromPos(pos)
        self.setZoomFactor(self.zoom * (1.0+self.ZOOM_WHEEL))
        elem_delta = elem_ori-self.mapPosFromPos(pos)
        self.scrollPos = self.scrollPos+elem_delta*self.zoom

    def zoomOut(self, pos=None):
        if pos is None:
            pos = QPointF(self.size().width()/2.0, self.size().height()/2.0)

        elem_ori = self.mapPosFromPos(pos)
        self.setZoomFactor(self.zoom*(1.0-self.ZOOM_WHEEL))
        elem_delta = elem_ori - self.mapPosFromPos(pos)
        self.scrollPos = self.scrollPos+elem_delta*self.zoom

    def wheelEvent(self, event: QWheelEvent):
        if (self.wheel_dir * event.angleDelta().y()) < 0:
            self.zoomIn(event.position())
        elif (self.wheel_dir * event.angleDelta().y()) > 0:
            self.zoomOut(event.position())

    def mousePressEvent(self, mouse_event: QMouseEvent):
        if not self.pressed and not self.scrolling and mouse_event.modifiers() == Qt.NoModifier:
            if mouse_event.buttons() == Qt.LeftButton:
                self.pressed = True
                self.scrolling = False
                self.handIsClosed = False
                QApplication.setOverrideCursor(Qt.OpenHandCursor)
                self.scrollMousePress = self.scrollPosition()
                self.positionMousePress = mouse_event.pos()
            elif mouse_event.buttons() == Qt.ForwardButton:
                self.webViewNavigateForward.emit()
            elif mouse_event.buttons() == Qt.BackButton:
                self.webViewNavigateBackward.emit()

    def mouseReleaseEvent(self, mouse_event: QMouseEvent):
        if self.scrolling:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            self.positionMousePress = None
            QApplication.restoreOverrideCursor()
            self.webViewIsScrolling.emit(False)
            return

        if self.pressed:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            QApplication.restoreOverrideCursor()
            return

    def hoveCheck(self, global_pos: QPoint, map_pos: QPoint) -> bool:
        return False

    def mouseDoubleClickEvent(self, mouse_event: QMouseEvent):
        self.webViewDoubleClicked.emit(self.mapPosFromEvent(mouse_event))

    def mapPosFromPos(self, pos: QPointF) -> QPointF:
        return (pos + self.scrollPos) / self.zoom

    def mapPosFromPoint(self, mouse_event: QPoint) -> QPointF:
        return (QPointF(mouse_event) + self.scrollPos) / self.zoom

    def mapPosFromEvent(self, mouse_event: QMouseEvent) -> QPointF:
        return (QPointF(mouse_event.pos()) + self.scrollPos) / self.zoom

    def mouseMoveEvent(self, mouse_event: QMouseEvent):
        if self.scrolling:
            if not self.handIsClosed:
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(Qt.OpenHandCursor)
                self.handIsClosed = True
            if self.scrollMousePress is not None:
                delta = mouse_event.pos() - self.positionMousePress
                self._setScrollPosition(self.scrollMousePress - delta)
        elif self.pressed:
            self.pressed = False
            self.scrolling = True
            self.webViewIsScrolling.emit(True)
        elif self.hoveCheck:
            self.hoveCheck(mouse_event.globalPos(), self.mapPosFromEvent(mouse_event))

    def event(self, event) -> bool:
        if event.type() == QEvent.ToolTip:
            event.ignore()
            return True
        return super(PanningWebView, self).event(event)
