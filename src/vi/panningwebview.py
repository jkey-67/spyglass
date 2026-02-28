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

import PySide6.QtCore
import numpy as np
import math
from typing import Tuple, Optional
from PySide6.QtCore import QPoint, QPointF, Signal, QSizeF, QRectF
from PySide6.QtCore import Qt
from PySide6.QtCore import QPropertyAnimation, Property
from PySide6.QtCore import Slot
from PySide6 import QtOpenGLWidgets
from vi.universe import Position
from vi.system import ALL_SYSTEMS,System,ALL_STARGATES
from vi.starmapwidget import StarMapWidget,select_font_family,generate_font_atlas,ConnectionLineGroups
from typing import Iterable, List
from string import printable
from vi.cache import cache

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
        id_src = stargate.system_id
        id_dst = stargate.destination.system_id
        if id_src is None or id_dst is None:
            continue
        if id_src > 31999999 or id_dst > 31999999:
            continue
        sys_src = ALL_SYSTEMS.get(id_src)
        sys_dst = ALL_SYSTEMS.get(id_dst)
        if sys_src is None or sys_dst is None:
            continue
        key = (id_src, id_dst) if id_src < id_dst else (id_dst, id_src)
        if key in pairs:
            continue
        pairs.add(key)
        pos = [sys_src.x, sys_src.y, sys_src.z, sys_dst.x, sys_dst.y, sys_dst.z]
        if grouped:
            region_a = sys_src.region_id
            region_b = sys_dst.region_id
            const_a = sys_src.constellation_id
            const_b = sys_dst.constellation_id
            if Position.USE_3D:
                gate_src = ALL_STARGATES.get(stargate.stargate_id)
                gate_dst = ALL_STARGATES.get(stargate.destination.stargate_id)
                pos[0] += gate_src.x
                pos[1] += gate_src.y
                pos[2] += gate_src.z
                pos[3] += gate_dst.x
                pos[4] += gate_dst.y
                pos[5] += gate_dst.z

            if region_a is not None and region_b is not None and region_a != region_b:
                cross_region.extend(pos)
            elif const_a is not None and const_b is not None and const_a != const_b:
                cross_constellation.extend(pos)
            else:
                standard.extend(pos)
        else:
            verts.extend(pos)

    if grouped:
        return ConnectionLineGroups(
            np.array(standard, dtype=np.float32),
            np.array(cross_constellation, dtype=np.float32),
            np.array(cross_region, dtype=np.float32),
        )

    if not verts:
        return np.array([], dtype=np.float32)
    return np.array(verts, dtype=np.float32)


def _bezier_segments( a: System, b: System|None, segments, bulge_factor) -> List[float]:
        """Build flat-ish quadratic Bezier segments between two systems.

        Args:
            a: Source system.
            b: Destination system.

        Returns:
            Flattened list of vertex pairs representing the curve.
        """
        ax, ay, az = a.x, a.y, a.z
        if b is None:
            bx, by, bz = a.x+0.035, a.y+0.045, a.z
        else:
            bx, by, bz = b.x, b.y, b.z
        dx = bx - ax
        dy = by - ay
        dist = math.hypot(dx, dy)
        if dist <= 1e-5:
            return []
        # Build a control point halfway along the edge, nudged perpendicular
        # to keep the curve nearly flat.
        px = -dy
        py = dx
        perp_len = math.hypot(px, py) or 1.0
        px /= perp_len
        py /= perp_len
        height = dist * bulge_factor
        cx = (ax + bx) * 0.5 + px * height
        cy = (ay + by) * 0.5 + py * height
        cz = (az + bz) * 0.5
        points: List[Tuple[float, float, float]] = []
        for i in range(segments + 1):
            t = i / float(segments)
            omt = 1.0 - t
            x = omt * omt * ax + 2.0 * omt * t * cx + t * t * bx
            y = omt * omt * ay + 2.0 * omt * t * cy + t * t * by
            z = omt * omt * az + 2.0 * omt * t * cz + t * t * bz
            points.append((x, y, z))
        segments: List[float] = []
        for i in range(len(points) - 1):
            x0, y0, z0 = points[i]
            x1, y1, z1 = points[i + 1]
            segments.extend([x0, y0, z0, x1, y1, z1])
        return segments

def load_jump_bridges(
    bridges,
    systems,
    segments: int = 32,
    bulge_factor: float = 0.16,
) -> np.ndarray:
    """Load jump-bridge style connections defined by system names.

    The file format is: ``<id> <source> --> <target>`` with ``#`` comments.
    Curves are emitted as a list of line segments approximating a quadratic
    Bezier with a gentle perpendicular bulge.

    Args:
        bridges: list of jump bridge file.
        systems: Systems to match names against.
        segments: Number of segments per curve.
        bulge_factor: Perpendicular bulge factor for the curve.

    Returns:
        Float32 array of line segment vertices.
    """
    systems_by_name = {sys.name: sys for sys in systems.values()}
    vertices: List[float] = []
    pairs = set()

    for src_name,_,dst_name in bridges:
        if src_name not in systems_by_name or dst_name not in systems_by_name:
            continue
        key = tuple(sorted((src_name, dst_name)))
        if key in pairs:
            continue
        pairs.add(key)
        a = systems_by_name[src_name]
        b = systems_by_name[dst_name]
        vertices.extend(_bezier_segments(a, b, segments, bulge_factor))

    if not vertices:
        return np.array([], dtype=np.float32)
    return np.array(vertices, dtype=np.float32)

def load_thera_jump_bridges(
    bridges,
    systems,
    segments: int = 16,
    bulge_factor: float = 0.3,
) -> np.ndarray:
    """Load jump-bridge style connections defined by system names.

    The file format is: ``<id> <source> --> <target>`` with ``#`` comments.
    Curves are emitted as a list of line segments approximating a quadratic
    Bezier with a gentle perpendicular bulge.

    Args:
        bridges: list of jump bridge file.
        systems: Systems to match names against.
        segments: Number of segments per curve.
        bulge_factor: Perpendicular bulge factor for the curve.

    Returns:
        Float32 array of line segment vertices.
    """
    systems_by_name = {sys.name: sys for sys in systems.values()}
    vertices: List[float] = []
    pairs = set()

    for src in bridges:
        src_name = src.get("in_system_name")
        dst_name = src.get("out_system_name")
        if src_name not in systems_by_name or dst_name not in systems_by_name:
            continue
        key = tuple(sorted((src_name, dst_name)))
        if key in pairs:
            continue
        pairs.add(key)
        a = systems_by_name[src_name]
        # b = systems_by_name[dst_name]
        # b = None
        vertices.extend(_bezier_segments(a, None, segments, bulge_factor))

    if not vertices:
        return np.array([], dtype=np.float32)
    return np.array(vertices, dtype=np.float32)


class PanningWebView(StarMapWidget):
    ZOOM_WHEEL = float(0.3)
    webViewNavigateForward = Signal()
    webViewNavigateBackward = Signal()
    webViewDoubleClicked = Signal(QPointF)

    def __init__(self, parent=None,show_jumpbridges: bool = True,show_timers: bool = True,show_statistic: bool = True ):
        """Initialize the widget state and input handling."""
        curr_cache = cache.Cache()
        systems = ALL_SYSTEMS
        stargates = ALL_STARGATES
        line_vertices =_load_connections(stargates.values(),grouped=True)
        chars = _collect_name_chars(systems.values())
        atlas_dir = os.path.join(os.path.dirname(__file__), "atlas")
        font_family = select_font_family(["Noto Sans CJK", "Noto Sans"])
        _, atlas_json = generate_font_atlas(atlas_dir, font_family, 32, chars, logical_font_size=8)
        jump_bridge_vertices = load_jump_bridges( curr_cache.getJumpGates(),ALL_SYSTEMS )
        thera_bridge_vertices = load_thera_jump_bridges(curr_cache.getThreaConnections(),ALL_SYSTEMS)


        super(PanningWebView, self).__init__(
            systems=systems,
            atlas_path=atlas_json,
            line_vertices=line_vertices,
            jump_bridge_vertices=jump_bridge_vertices,
            thera_bridge_vertices=thera_bridge_vertices,
            mouse_3d=Position.USE_3D,
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
        # QOpenGLWidget should render as an opaque surface; transparent widget
        # flags can cause compositor artifacts while panning.
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setUpdateBehavior(QtOpenGLWidgets.QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
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

    def updateContent(self)->None:
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

    def hoverCheck(self,global_pos: QPoint, system_id: int|None):
        pass

    def event(self, event) -> bool:
        """Override event handling for tooltip suppression.

        Args:
            event (QEvent): Incoming event.

        Returns:
            bool: True if handled, otherwise defer to base class.
        """
        if event.type() == PySide6.QtCore.QEvent.Type.ToolTip:
            system_id = self.objectUnderMouse(event.pos())
            if system_id:
                self._hovered_system = ALL_SYSTEMS.get(system_id)
                self.hoverCheck(event.globalPos(),system_id )
                event.ignore()
                return True
        return super(PanningWebView, self).event(event)

    @Slot()
    def updateJumpBridgesFromCache(self):
        self.updateJumpBridges(load_jump_bridges(cache.Cache().getJumpGates(), ALL_SYSTEMS))

    @Slot()
    def updateWormholeBridgesFromCache(self):
        self.updateWormholeBridges(load_thera_jump_bridges(cache.Cache().getThreaConnections(), ALL_SYSTEMS))

    @Slot(bool)
    def showJumpBridges(self,val):
        self.show_jumpbridges = val

    @Slot(bool)
    def showStatistics(self,val):
        self.show_statistic = val

    @Slot(bool)
    def showTimers(self,val):
        self.show_timers = val

