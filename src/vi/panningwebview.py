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

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QResizeEvent, QWheelEvent, QMouseEvent, QTransform
from PySide6.QtCore import QPoint, QPointF, Signal, QSizeF, QRectF
from PySide6.QtCore import Qt, QEvent
from PySide6.QtCore import QPropertyAnimation, Property
from PySide6.QtOpenGLWidgets import QOpenGLWidget

class PanningWebView(QWidget):
    ZOOM_WHEEL = float(0.3)
    webViewIsScrolling = Signal(bool)
    webViewUpdateScrollbars = Signal()
    webViewNavigateForward = Signal()
    webViewNavigateBackward = Signal()
    webViewDoubleClicked = Signal(QPointF)

    def __init__(self, parent=None):
        """Initialize the widget state and input handling."""
        super(PanningWebView, self).__init__(parent)
        self.content = None
        self.transform = QTransform()
        self.zoom = 1.0
        self.wheel_dir = 1.0
        self.pressed = False
        self.scrolling = False
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._scrollPos = QPointF(0.0, 0.0)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.animation = QPropertyAnimation(self, b"propScrollPos")

    @Property(QPointF)
    def propScrollPos(self)->QPointF:
        """QProperty getter for the current scroll position."""
        return self._scrollPos

    @propScrollPos.setter
    def propScrollPos(self, val):
        """QProperty setter for the current scroll position.

        Args:
            val (QPointF): New scroll position.
        """
        if val and self._scrollPos != val:
            self._scrollPos = val
            self.update()
            self.webViewUpdateScrollbars.emit()

    @Property(QSizeF)
    def imgRect(self) -> QRectF:
        """Return the content size for layout calculations.

        Returns:
            QSizeF: Size of the map content.
        """
        if self.content:
            return self.content.map_rect
        else:
            return QRectF()

    def setContent(self, content)->None:
        """Set the content provider for rendering.

        The content object must provide:
        - content.svg_size (QSizeF)
        - content.renderMap(QPainter) -> None
        - content.renderLegend(QPainter) -> None

        Args:
            content: Content provider used for rendering.
        """
        if self.scrolling:
            return
        if self.content != content:
            self.content = content
            self.webViewUpdateScrollbars.emit()
        self.update()

    def resizeEvent(self, event: QResizeEvent)->None:
        """Handle resize events and refresh scrollbars.

        Args:
            event (QResizeEvent): Resize event data.
        """
        super().resizeEvent(event)
        self.webViewUpdateScrollbars.emit()

    def paintEvent(self, event)->None:
        """Render the map and legend.

        Args:
            event (QPaintEvent): Paint event data.
        """
        if self.content is None:
            return
        try:
            with QPainter(self) as painter:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.transform.reset()
                self.transform.translate(-self.propScrollPos.x(), -self.propScrollPos.y())
                self.transform.scale(self.zoom, self.zoom)
                painter.setTransform(self.transform)
                self.content.renderMap(painter,self.zoom)
                self.transform.reset()
                painter.setTransform(self.transform)
                self.content.renderLegend(painter)
        finally:
            self.transform.reset()

    @Property(float)
    def zoomFactor(self)->float:
        """Return the current zoom factor.

        Returns:
            float: Current zoom value.
        """
        return self.zoom

    @zoomFactor.setter
    def zoomFactor(self, zoom: float)->None:
        """Set the zoom factor with clamping.

        Args:
            zoom (float): Requested zoom factor.
        """
        if zoom > 6.0:
            zoom = 6.0
        elif zoom < 0.025:
            zoom = 0.025
        if self.zoom != zoom:
            self.zoom = zoom
            self.webViewUpdateScrollbars.emit()

    def scrollPositionFromMapCoordinate(self, pt_system: QRectF)->QPointF:
        """Calculate the scroll position for centering a map rectangle.

        Args:
            pt_system (QRectF): Map rectangle to center.

        Returns:
            QPointF: Scroll position that centers the rectangle.
        """
        return QPointF(pt_system.center().x() * self.zoom - 0.5*self.size().width(),
                       pt_system.center().y() * self.zoom - 0.5*self.size().height())

    def setScrollPosition(self, pos: QPointF, animate=False):
        """Set the scroll position, optionally animated.

        Args:
            pos (QPointF): Target scroll position.
            animate (bool): Whether to animate the transition.
        """
        if not self.scrolling:
            if animate:
                self.animation.stop()
                self.animation.setDuration(75)
                self.animation.setStartValue(self.propScrollPos)
                self.animation.setEndValue(pos)
                self.animation.start()
            else:
                self.propScrollPos = pos

    def setZoomAndScrollPos(self, zoom, pos):
        """Update zoom and scroll position together.

        Args:
            zoom (float): Target zoom value.
            pos (QPointF): Target scroll position.
        """
        if self.scrolling:
            return

        if zoom and self.zoom != zoom:
            if zoom > 8.0:
                zoom = 8.0
            elif zoom < 0.125:
                zoom = 0.125
            if self.zoom != zoom:
                self.zoom = zoom

        if pos and self.propScrollPos != pos:
            if self.propScrollPos != pos:
                self.propScrollPos = pos

    def zoomIn(self, pos=None)->None:
        """Zoom in around a widget position.

        Args:
            pos (QPointF | None): Widget position to anchor zoom.
        """
        if self.scrolling:
            return

        if pos is None:
            pos = QPointF(self.size().width()/2.0, self.size().height()/2.0)

        elem_ori = self.mapPosFromPos(pos)
        self.zoomFactor =  self.zoomFactor * (1.0+self.ZOOM_WHEEL)
        elem_delta = elem_ori-self.mapPosFromPos(pos)
        self.propScrollPos = self.propScrollPos+elem_delta*self.zoom

    def zoomOut(self, pos=None)->None:
        """Zoom out around a widget position.

        Args:
            pos (QPointF | None): Widget position to anchor zoom.
        """
        if pos is None:
            pos = QPointF(self.size().width()/2.0, self.size().height()/2.0)

        elem_ori = self.mapPosFromPos(pos)
        self.zoomFactor = self.zoom*(1.0-self.ZOOM_WHEEL)
        elem_delta = elem_ori - self.mapPosFromPos(pos)
        self.propScrollPos = self.propScrollPos+elem_delta*self.zoom

    def wheelEvent(self, event: QWheelEvent)->None:
        """Handle mouse wheel zooming.

        Args:
            event (QWheelEvent): Wheel event data.
        """
        if (self.wheel_dir * event.angleDelta().y()) < 0:
            self.zoomIn(event.position())
        elif (self.wheel_dir * event.angleDelta().y()) > 0:
            self.zoomOut(event.position())

    def mousePressEvent(self, mouse_event: QMouseEvent)->None:
        """Handle mouse press events for panning and navigation.

        Args:
            mouse_event (QMouseEvent): Mouse press event data.
        """
        if not self.pressed and not self.scrolling and mouse_event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if mouse_event.buttons() == Qt.MouseButton.LeftButton:
                self.pressed = True
                self.scrolling = False
                self.handIsClosed = False
                QApplication.setOverrideCursor(Qt.CursorShape.OpenHandCursor)
                self.scrollMousePress = self.propScrollPos
                self.positionMousePress = mouse_event.pos()
            elif mouse_event.buttons() == Qt.MouseButton.ForwardButton:
                self.webViewNavigateForward.emit()
            elif mouse_event.buttons() == Qt.MouseButton.BackButton:
                self.webViewNavigateBackward.emit()

    def mouseReleaseEvent(self, mouse_event: QMouseEvent)->None:
        """Handle mouse release events and reset state.

        Args:
            mouse_event (QMouseEvent): Mouse release event data.
        """
        if self.scrolling:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            self.positionMousePress = None
            if QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()
            self.webViewIsScrolling.emit(False)
            return

        if self.pressed:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            if QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()
            return

    def hoveCheck(self, global_pos: QPoint, map_pos: QPointF) -> bool:
        """Optional hover check for subclasses.

        Args:
            global_pos (QPoint): Global mouse position.
            map_pos (QPointF): Map position.

        Returns:
            bool: Whether the hover was handled.
        """
        return False

    def mouseDoubleClickEvent(self, mouse_event: QMouseEvent)->None:
        """Handle mouse double-click events.

        Args:
            mouse_event (QMouseEvent): Mouse double-click event data.
        """
        self.webViewDoubleClicked.emit(self.mapPosFromEvent(mouse_event))

    def mapPosFromPos(self, pos: QPointF) -> QPointF:
        """Convert a widget position to map coordinates.

        Args:
            pos (QPointF): Widget position.

        Returns:
            QPointF: Map coordinates.
        """
        return (pos + self.propScrollPos) / self.zoom

    def mapPosFromPoint(self, mouse_event: QPoint) -> QPointF:
        """Convert a widget point to map coordinates.

        Args:
            mouse_event (QPoint): Widget point.

        Returns:
            QPointF: Map coordinates.
        """
        return (QPointF(mouse_event) + self.propScrollPos) / self.zoom

    def mapPosFromEvent(self, mouse_event: QMouseEvent) -> QPointF:
        """Convert a mouse event position to map coordinates.

        Args:
            mouse_event (QMouseEvent): Mouse event data.

        Returns:
            QPointF: Map coordinates.
        """
        return (QPointF(mouse_event.pos()) + self.propScrollPos) / self.zoom

    def mouseMoveEvent(self, mouse_event: QMouseEvent):
        """Handle mouse move events for panning and hover.

        Args:
            mouse_event (QMouseEvent): Mouse move event data.
        """
        if self.scrolling:
            if not self.handIsClosed:
                if QApplication.overrideCursor():
                    QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(Qt.CursorShape.OpenHandCursor)
                self.handIsClosed = True
            if self.scrollMousePress is not None and self.positionMousePress is not None:
                delta = mouse_event.pos() - self.positionMousePress
                self.propScrollPos = self.scrollMousePress - delta
        elif self.pressed:
            self.pressed = False
            self.scrolling = True
            self.webViewIsScrolling.emit(True)
        elif self.hoveCheck:
            self.hoveCheck(mouse_event.globalPos(), self.mapPosFromEvent(mouse_event))

    def event(self, event) -> bool:
        """Override event handling for tooltip suppression.

        Args:
            event (QEvent): Incoming event.

        Returns:
            bool: True if handled, otherwise defer to base class.
        """
        if event.type() == QEvent.Type.ToolTip:
            event.ignore()
            return True
        return super(PanningWebView, self).event(event)
