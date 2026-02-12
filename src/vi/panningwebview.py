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
import numpy as np
from PySide6.QtCore import QPoint, QPointF, Signal, QSizeF, QRectF
from PySide6.QtCore import Qt
from PySide6.QtCore import QPropertyAnimation, Property

from vi.universe import Universe
from vi.system import ALL_SYSTEMS,System,ALL_STARGATES
from vi.starmapwidget import StarMapWidget,select_font_family,generate_font_atlas,ConnectionLineGroups
from typing import Iterable, List
from string import printable

def _collect_name_chars(systems: Iterable[System]) -> List[str]:
    """Collect all unique characters from system names.

    Args:
        systems: Systems to scan for label characters.

    Returns:
        Sorted list of unique characters.
    """
    chars = set(printable)
    for sys in systems:
        for ch in sys.name:
            chars.add(ch)
    return sorted(chars)

def _load_connections(
    stargates,
    *,
    grouped: bool = False,
) -> np.ndarray | ConnectionLineGroups:
    """Load stargate connections into a flat vertex array.

    Args:
        path: Path to the stargates JSONL file.
        systems: Systems to match IDs against.
        grouped: If True, returns vertices split into groups based on whether
            the connection crosses constellations/regions.

    Returns:
        Either a float32 array of line vertices (x, y, z pairs), or a
        ConnectionLineGroups instance when ``grouped`` is True.
    """
    pairs = set()
    verts: List[float] = []
    standard: List[float] = []
    cross_constellation: List[float] = []
    cross_region: List[float] = []
    for stargate in stargates:
        src = stargate.get("system_id")
        dst = stargate.get("destination", {}).get("system_id")
        if src is None or dst is None:
            continue
        if src > 31999999 or dst > 31999999:
            continue
        a = Universe.systemById(src)
        b = Universe.systemById(dst)
        if a is None or b is None:
            continue
        key = (src, dst) if src < dst else (dst, src)
        if key in pairs:
            continue
        pairs.add(key)
        a = ALL_SYSTEMS.get(src)
        b = ALL_SYSTEMS.get(dst)
        if grouped:
            region_a = a.region_id
            region_b = b.region_id
            const_a = a.constellation_id
            const_b = b.constellation_id
            if region_a is not None and region_b is not None and region_a != region_b:
                cross_region.extend([a.x, a.y, a.z, b.x, b.y, b.z])
            elif const_a is not None and const_b is not None and const_a != const_b:
                cross_constellation.extend([a.x, a.y, a.z, b.x, b.y, b.z])
            else:
                standard.extend([a.x, a.y, a.z, b.x, b.y, b.z])
        else:
            verts.extend([a.x, a.y, a.z, b.x, b.y, b.z])

    if grouped:
        return ConnectionLineGroups(
            np.array(standard, dtype=np.float32),
            np.array(cross_constellation, dtype=np.float32),
            np.array(cross_region, dtype=np.float32),
        )

    if not verts:
        return np.array([], dtype=np.float32)
    return np.array(verts, dtype=np.float32)


class PanningWebView(StarMapWidget):
    ZOOM_WHEEL = float(0.3)
    webViewNavigateForward = Signal()
    webViewNavigateBackward = Signal()
    webViewDoubleClicked = Signal(QPointF)

    def __init__(self, parent=None):
        """Initialize the widget state and input handling."""
        systems = ALL_SYSTEMS
        stargates = ALL_STARGATES
        line_vertices =_load_connections(stargates.values(),grouped=True)
        use_mouse_3d = False
        chars = _collect_name_chars(systems.values())
        atlas_dir = os.path.join(os.path.dirname(__file__), "atlas")
        font_family = select_font_family(["Noto Sans CJK", "Noto Sans"])
        _, atlas_json = generate_font_atlas(atlas_dir, font_family, 32, chars, logical_font_size=8)

        jump_bridge_vertices = np.array([], dtype=np.float32)

        super(PanningWebView, self).__init__(
            systems,
            atlas_json,
            line_vertices,
            jump_bridge_vertices,
            mouse_3d=use_mouse_3d,
            parent=parent,
        )
        self.pressed = False
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._scrollPos = QPointF(self.target[0], self.target[1])
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.animation = QPropertyAnimation(self, b"propScrollPos")

    @Property(QPointF)
    def propScrollPos(self)->QPointF:
        """QProperty getter for the current scroll position."""
        return QPointF(-self.target[0],-self.target[1])

    @propScrollPos.setter
    def propScrollPos(self, val):
        """QProperty setter for the current scroll position.

        Args:
            val (QPointF): New scroll position.
        """
        if self.panning or self.orbiting:
            return
        if val and self._scrollPos != val:
            self.target[0] = -val.x()
            self.target[1] = -val.y()
            self.camera_target[0] = self.target[0]
            self.camera_target[1] = self.target[1]
            self.camera_target[2] = 0.0
            self._scrollPos = val


    @Property(QSizeF)
    def imgRect(self) -> QRectF:
        """Return the content size for layout calculations.

        Returns:
            QSizeF: Size of the map content.
        """
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
        if not self._text_rebuild_pending:
            self._text_rebuild_pending = True

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
        if self.zoom != zoom:
            self.zoom = zoom

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
        if self.panning or self.orbiting:
            return
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
        if self.panning or self.orbiting:
            return

        if zoom and self.zoom != zoom:
            if self.zoom != zoom:
                self.zoom = zoom

    def zoomIn(self, pos=None)->None:
        """Zoom in around a widget position.

        Args:
            pos (QPointF | None): Widget position to anchor zoom.
        """
        if self.panning or self.orbiting:
            return
        self.zoom =  self.zoom * (1.0+self.ZOOM_WHEEL)

    def zoomOut(self, pos=None)->None:
        """Zoom out around a widget position.

        Args:
            pos (QPointF | None): Widget position to anchor zoom.
        """
        if self.panning or self.orbiting:
            return
        self.zoom =  self.zoom * (1.0-self.ZOOM_WHEEL)


    def hoveCheck(self, global_pos: QPoint, map_pos: QPointF) -> bool:
        """Optional hover check for subclasses.

        Args:
            global_pos (QPoint): Global mouse position.
            map_pos (QPointF): Map position.

        Returns:
            bool: Whether the hover was handled.
        """
        return False


    def mapPosFromPoint(self, mouse_event: QPoint) -> QPointF:
        """Convert a widget point to map coordinates.

        Args:
            mouse_event (QPoint): Widget point.

        Returns:
            QPointF: Map coordinates.
        """
        return (QPointF(mouse_event) + self.propScrollPos) / self.zoom



