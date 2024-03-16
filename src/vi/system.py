###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#    																	  #
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

###########################################################################
# Little lib and tool to get the map and information from dotlan		  #
###########################################################################

import math
import datetime
import json
import os

from PySide6.QtCore import QRectF, QPointF, Qt, QMargins, QLineF
from PySide6.QtGui import QPainter, QFont, QPen, QBrush, QColor, QRadialGradient, QPainterPath
from vi.states import States
from vi.cache import Cache
from vi.ui.styles import Styles, TextInverter
from vi.universe import Universe
from vi.globals import Globals


class System(object):
    """
        A System on the Map

        Attributes:
        ----------
        name: str
            The name of th system

        status: States see
            The current status of the system, one of the States enums, default is UNKNOWN


        ticker: str
            Ticker of the alliance holding the soverinity

        svgElement:object
            object referencing the xml element

        mapSoup:object
            object referencing the xml coup

        self.rect = svg_element.select("rect")[0]
        self.firstLine = svg_element.select("text")[0]
        self.secondLine = svg_element.select("text")[1]
        self.secondLineFlash = False
        self.lastAlarmTimestamp = 0
        self.messages = []
        self.backgroundColor = self.styles.getCommons()["bg_colour"]
        self.systemId = system_id
        self.transform = "translate(0, 0)" if transform is None else transform
        self.cachedOffsetPoint = None
        self.neighbours = set()
        self.statistics = {"jumps": "?", "shipkills": "?", "factionkills": "?", "podkills": "?"}
        self.currentStyle = ""
        self.__hasCampaigns = False
        self.__hasIncursion = False
        self.__isStaging = False
        self.__hasIncursionBoss = False
        self.svgtext = None

    """

    styles = Styles()
    textInv = TextInverter()
    SYSTEM_STYLE = "font-family: Arial, Helvetica, sans-serif; font-size: 8px; fill: {};"
    ALARM_STYLE = "font-family: Arial, Helvetica, sans-serif; font-size: 7px; fill: {};"

    ALARM_COLORS = [(1.0,  "#d00000", "#D09B0F", "#C0C0C0"),
                    (0.75, "#D09B0F", "#D0FA0F", "#C0C0C0"),
                    (0.5,  "#D0FA0F", "#D0FDA2", "#C0C0C0"),
                    (0.25, "#D0FDA2", "#BACKGD", "#C0C0C0"),
                    (0,    "#BACKGD", "#BACKGD", "#C0C0C0")]

    CLEAR_COLORS = [(1.0,  "#00FF00", "#40FF40", "#C0C0C0"),
                    (0.75, "#40FF40", "#80FF80", "#C0C0C0"),
                    (0.5,  "#80FF80", "#C0FFC0", "#C0C0C0"),
                    (0.25, "#C0FFC0", "#BACKGD", "#C0C0C0"),
                    (0.0,  "#BACKGD", "#BACKGD", "#C0C0C0")]

    ALARM_COLOR = ALARM_COLORS[0][1]
    UNKNOWN_COLOR = styles.getCommons()["unknown_colour"]
    CLEAR_COLOR = CLEAR_COLORS[0][1]

    ELEMENT_WIDTH = 62.5
    ELEMENT_HEIGHT = 30

    def __init__(self, name, system_id, ticker="-?-"):
        self.name = name
        self.system_id = system_id
        self.region_id = Universe.regionIDFromSystemID(system_id)
        system_data = Universe.systemById(self.system_id)
        self.constellation_id = system_data["constellation_id"]
        self.ticker = ticker
        self._system_messages = []
        self.jumpBridges = set()
        self.theraWormholes = set()
        self.backgroundAlpha = 1.0
        self.backgroundColor = self.UNKNOWN_COLOR
        self.backgroundColorNext = self.UNKNOWN_COLOR
        self.statusTextColor = "#FFFFFF"

        self.rect = QRectF(0.0, 0.0, 64.0, 32.0)
        self.marker = 0.0
        self.wormhole_info = list()

        self.is_vulnerable_visible = True
        self.is_statistics_visible = True
        self.is_jumpbridges_visible = True

        self._is_dirty = True
        self._status = None
        self._first_line = self.name
        self._second_line = ticker
        self._second_line_flash = False
        self._last_alarm_timestamp = 0
        self._locatedCharacters = []
        self._neighbours = None
        self._hasCampaigns = False
        self._hasIncursion = False
        self._hasIceBelt = False
        self._isStaging = False
        self._hasIncursionBoss = False
        self._hasThera = False
        self._isMonitored = 0
        self._hasKill = 0.0
        self._svg_text_string = "stats n/a"
        self._alarm_seconds = 0
        # C cloning, R Refining, F Factory, R Research, O Offices, I Industry
        self._hasKeepStar = set()  # set of station services
        # C cloning, R Refining, F Factory, R Research, O Offices, I Industry
        self._hasStation = set()   # set of station services

        self.vulnerability_occupancy_level = None
        self.vulnerable_end_time = None
        self.vulnerable_start_time = None
        self._vulnerability_text = None

        self.marking_color = None
        self.marking_scale = 1.0

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty or self._hasKill > 0.0 or self.marker != 0.0 or self._status is not States.UNKNOWN

    @property
    def status(self):
        """
        Laze evaluated status for the system, background and second line flash is adjusted.
        Returns:
            The status of the system States.UNKNOWN, States.ALARM or States.CLEAR
        """
        if self._status is None:
            if len(self._system_messages):
                msg = self._system_messages[-1]
                self._last_alarm_timestamp = msg.timestamp.timestamp()
                self._status = msg.status
            else:
                self._status = States.UNKNOWN
            if self._status == States.ALARM:
                self.setBackgroundColor(self.ALARM_COLOR)
            elif self._status == States.CLEAR:
                self.setBackgroundColor(self.CLEAR_COLOR)
            elif self._status == States.UNKNOWN:
                self.setBackgroundColor(self.UNKNOWN_COLOR)
                self._second_line_flash = False
        return self._status

    def renderConnections(self, painter: QPainter, current_region_id, systems):
        """
        Renders the connections in between the systems
        Args:
            painter:
                QPainter to use
            current_region_id:
                id of current region
            systems: dict of all systems, key is system name

        Returns:
            None

        """
        painter.setPen(QColor("#ffc0c0c0"))
        for system in self.neighbours:
            if system.name in systems.keys():
                if self.region_id == current_region_id:
                    if self.constellation_id == system.constellation_id:
                        painter.setPen(QColor("#60c0c0c0"))
                    else:
                        painter.setPen(QColor("#60ff0000"))
                else:
                    painter.setPen(QColor("#60c71585"))
                painter.drawLine(QLineF(self.center, system.center))
                painter.setPen(Qt.NoPen)

    @staticmethod
    def renderLegend(painter: QPainter, region_name):
        painter.setFont(QFont("Arial", 30, italic=True))
        painter.setPen(QColor("#10c0c0c0"))
        painter.drawText(QRectF(0.0, 0.0, 1024.0, 50.0), Qt.AlignLeft, region_name)
        # System.testRender(painter)

    @staticmethod
    def testRender(painter: QPainter):
        system_id = Universe.systemIdByName("Umokka")
        region_id = Universe.regionIDFromSystemID(system_id)
        inx = 1
        test = System("Name", system_id, "Ticker")
        test._first_line = "XXXX"
        test._second_line = "YYYYY"
        test.applySVG(QRectF(20.0, inx*50.0, System.ELEMENT_WIDTH, System.ELEMENT_HEIGHT))
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)

        inx = inx + 1
        test._hasCampaigns = True
        test.rect.moveTop(inx * 50.0)
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)

        inx = inx + 1
        test._hasCampaigns = False
        test._hasIceBelt = True
        test.rect.moveTop(inx * 50.0)
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)

        inx = inx + 1
        test._hasCampaigns = False
        test._hasIceBelt = False
        test._hasIncursion = True
        test.rect.moveTop(inx * 50.0)
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)

        inx = inx + 1
        test._hasCampaigns = False
        test._hasIceBelt = False
        test._hasIncursion = False
        test._isMonitored = 1
        test.rect.moveTop(inx * 50.0)
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)

        inx = inx + 1
        test._hasCampaigns = False
        test._hasIceBelt = False
        test._hasIncursion = False
        test._isMonitored = 0
        test._locatedCharacters = ["Test"]
        test.rect.moveTop(inx * 50.0)
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)

        inx = inx + 1
        test._hasCampaigns = False
        test._hasIceBelt = False
        test._hasIncursion = False
        test._isMonitored = 0
        test._locatedCharacters = None
        test._hasKill = 1.0
        test.rect.moveTop(inx * 50.0)
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)

        inx = inx + 1
        test._hasCampaigns = False
        test._hasIceBelt = False
        test._hasIncursion = False
        test._isMonitored = 0
        test._locatedCharacters = None
        test._hasKill = 10.0
        test.rect.moveTop(inx * 50.0)
        test.renderBackground(painter, region_id)
        test.renderSystemTexts(painter, region_id)
        pass

    def renderWormHoles(self, painter: QPainter, current_region_id, systems):
        """
        Renders the wormhole connections for Thera and Tumor
        Args:
            painter:
            current_region_id:
            systems:

        Returns:

        """
        if not self.is_jumpbridges_visible:
            return
        for system in self.theraWormholes:
            painter.setPen(QColor("#c0ffff00"))
            if system.name in systems.keys():
                if self.name < system.name:
                    pos_a = self.rect.center()
                    pos_b = system.rect.center()
                else:
                    pos_b = self.rect.center()
                    pos_a = system.rect.center()

                dx = (pos_b.x() - pos_a.x())/2.0
                dy = (pos_b.y() - pos_a.y())/2.0
                offset = 0.4 * math.sqrt(dx*dx+dy*dy)
                angle = math.atan2(dy, dx) - math.pi / 2.0
                pos_m = QPointF(pos_a.x() + dx + offset * math.cos(angle), pos_a.y() + dy + offset * math.sin(angle))
                path = QPainterPath()
                path.moveTo(pos_a)
                path.cubicTo(pos_m, pos_b, pos_b)
                painter.drawPath(path)
            else:
                pos_a = self.rect.center()
                pos_b = self.rect.center()+QPointF(20, -20)
                dx = (pos_b.x() - pos_a.x())/2.0
                dy = (pos_b.y() - pos_a.y())/2.0
                offset = 0.4 * math.sqrt(dx*dx+dy*dy)
                angle = math.atan2(dy, dx) - math.pi / 2.0
                pos_m = QPointF(pos_a.x() + dx + offset * math.cos(angle), pos_a.y() + dy + offset * math.sin(angle))
                path = QPainterPath()
                path.moveTo(pos_a)
                path.cubicTo(pos_m, pos_b, pos_b)
                painter.drawPath(path)
                old_translate = painter.transform().__copy__()
                painter.translate(pos_b.x(), pos_b.y())
                painter.rotate(+30)
                painter.setFont(QFont("Arial", self.ELEMENT_HEIGHT / 8 * 1.5))
                painter.drawText(QRectF(-30.0, -10.0, 60.0, 10.0), Qt.AlignCenter, system.name)
                painter.setTransform(old_translate)

    def renderJumpBridges(self, painter: QPainter, current_region_id, systems):
        """
        Renders all jumpbridge connections
        Args:
            painter:
            current_region_id:
            systems:

        Returns:

        """
        if not self.is_jumpbridges_visible:
            return
        for system in self.jumpBridges:
            if system.name in systems.keys():
                if self.region_id == current_region_id:
                    if self.constellation_id == system.constellation_id:
                        painter.setPen(QColor("#407cfc00"))
                    else:
                        painter.setPen(QColor("#407cfc00"))
                else:
                    painter.setPen(QColor("#407cfc00"))
                # sorting enabled to paint each paired connection AB and BA in the same way
                if self.name < system.name:
                    pos_a = self.rect.center()
                    pos_b = system.rect.center()
                else:
                    pos_b = self.rect.center()
                    pos_a = system.rect.center()

                dx = (pos_b.x() - pos_a.x())/2.0
                dy = (pos_b.y() - pos_a.y())/2.0
                offset = 0.4 * math.sqrt(dx*dx+dy*dy)
                angle = math.atan2(dy, dx) - math.pi / 2.0
                pos_m = QPointF(pos_a.x() + dx + offset * math.cos(angle), pos_a.y() + dy + offset * math.sin(angle))
                path = QPainterPath()
                path.moveTo(pos_a)
                path.cubicTo(pos_m, pos_b, pos_b)
                painter.drawPath(path)
            else:
                painter.setPen(QColor("#807cfc00"))
                pos_a = self.rect.center()
                pos_b = self.rect.center()+QPointF(20, -20)
                dx = (pos_b.x() - pos_a.x())/2.0
                dy = (pos_b.y() - pos_a.y())/2.0
                offset = 0.4 * math.sqrt(dx*dx+dy*dy)
                angle = math.atan2(dy, dx) - math.pi / 2.0
                pos_m = QPointF(pos_a.x() + dx + offset * math.cos(angle), pos_a.y() + dy + offset * math.sin(angle))
                path = QPainterPath()
                path.moveTo(pos_a)
                path.cubicTo(pos_m, pos_b, pos_b)
                painter.drawPath(path)
                old_translate = painter.transform().__copy__()
                painter.translate(pos_b.x(), pos_b.y())
                painter.rotate(+30)
                painter.setFont(QFont("Arial", self.ELEMENT_HEIGHT / 8 * 1.5))
                painter.drawText(QRectF(-30.0, -10.0, 60.0, 10.0), Qt.AlignCenter, system.name)
                painter.setTransform(old_translate)

    def renderBackground(self, painter: QPainter, current_region_id):
        """
        Renders th background for the map, _hasIncursion, _hasCampaigns, _locatedCharacters and marker will be handled
        Args:
            painter:
            current_region_id:

        Returns:

        """
        rc_out_back = self.rect.__copy__().marginsAdded(QMargins(20, 20, 20, 20))
        delta_h = self.ELEMENT_HEIGHT / 2
        delta_w = self.ELEMENT_WIDTH / 2

        if self.marking_color:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.marking_color))
            path = QPainterPath()
            scale = self.marking_scale
            factor_a = 0.8 * scale
            factor_a_y = 1.0 * scale
            factor_b = 1.125 * scale
            path.moveTo(self.rect.center().x() - delta_w * factor_a, self.rect.center().y() - delta_h * factor_a_y)
            path.lineTo(self.rect.center().x() + delta_w * factor_a, self.rect.center().y() - delta_h * factor_a_y)
            path.lineTo(self.rect.center().x() + delta_w * factor_b, self.rect.center().y() - delta_h * 0.0)
            path.lineTo(self.rect.center().x() + delta_w * factor_a, self.rect.center().y() + delta_h * factor_a_y)
            path.lineTo(self.rect.center().x() - delta_w * factor_a, self.rect.center().y() + delta_h * factor_a_y)
            path.lineTo(self.rect.center().x() - delta_w * factor_b, self.rect.center().y() + delta_h * 0.0)

            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

        if self._hasIncursion:
            gradient = QRadialGradient(self.rect.center(), self.ELEMENT_WIDTH)
            gradient.setColorAt(0.0, QColor("#30ffd700"))
            if self._hasIncursionBoss:
                gradient.setColorAt(0.5, QColor("#10ff4500"))
                gradient.setColorAt(0.6, QColor("#00ff4500"))
            else:
                gradient.setColorAt(0.6, QColor("#00ffd700"))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(rc_out_back, delta_h, delta_h)

            for i in range(int(-delta_w), int(delta_w), 5):
                gradient.setCenter(rc_out_back.center().x()+i, rc_out_back.center().y())
                painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)

        if self._hasCampaigns:
            gradient = QRadialGradient(self.rect.center(), self.ELEMENT_WIDTH)
            gradient.setColorAt(0.0, QColor("#30ff0000"))
            gradient.setColorAt(0.6, QColor("#00ff0000"))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(rc_out_back, delta_h, delta_h)
            for i in range(int(-delta_w), int(delta_w), 5):
                gradient.setCenter(rc_out_back.center().x()+i, rc_out_back.center().y())
                painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)

        if self._isMonitored > 0:
            rc_out_back_monitor = self.rect.__copy__().marginsAdded(QMargins(80, 80, 80, 80))
            gradient = QRadialGradient(self.rect.center(), self.ELEMENT_WIDTH*1.25)
            gradient.setColorAt(0.0, QColor("#80ffffff"))
            gradient.setColorAt(0.6, QColor("#00ffffff"))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(rc_out_back_monitor, delta_h, delta_h)
            painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)

        if self._hasKill > 0.0:
            gradient = QRadialGradient(self.rect.center(), self.ELEMENT_WIDTH)
            col_red = QColor("#FF4500")
            col_red.setAlphaF(max(min(self._hasKill/20., 1.), 0.001))
            gradient.setColorAt(0.0, col_red)
            gradient.setColorAt(0.6, QColor("#00FF4500"))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(rc_out_back, delta_h, delta_h)
            for i in range(int(-delta_w), int(delta_w), 1):
                gradient.setCenter(rc_out_back.center().x()+i, rc_out_back.center().y())
                painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)
            self._hasKill = self._hasKill - 0.025

        if bool(self._locatedCharacters):
            gradient = QRadialGradient(self.rect.center(), self.ELEMENT_WIDTH)
            gradient.setColorAt(0.0, QColor("#30800080"))
            gradient.setColorAt(0.6, QColor("#00800080"))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(rc_out_back, delta_h, delta_h)
            for i in range(int(-delta_w), int(delta_w), 5):
                gradient.setCenter(rc_out_back.center().x()+i, rc_out_back.center().y())
                painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)

        if self.marker > datetime.datetime.utcnow().timestamp():
            gradient = QRadialGradient(self.rect.center(), self.ELEMENT_WIDTH)
            marker_color = QColor("#6495ed")
            marker_color.setAlphaF((self.marker-datetime.datetime.utcnow().timestamp())/10.0)

            gradient.setColorAt(0.0, marker_color)
            gradient.setColorAt(0.6, QColor("#006495ed"))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addEllipse(rc_out_back)
            gradient.setCenter(rc_out_back.center().x(), rc_out_back.center().y())
            painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)
        else:
            self.marker = 0.0

    def renderSystemTexts(self, painter: QPainter, current_region_id):
        """
        Renders the system to a painter and resets the dirty flag
        Args:
            painter: QPainter to use
            current_region_id: region id of map

        Returns:

        """
        delta_h = self.ELEMENT_HEIGHT / 8
        rc_out = self.rect.__copy__().marginsAdded(QMargins(-2, -2, -2, -2))
        painter.setBrush(self.getBackgroundBrush())
        if self.region_id == current_region_id:
            painter.setPen(QPen(QColor("#FFc0c0c0")))
            path = QPainterPath()
            path.addRoundedRect(rc_out, 12, 12)
            painter.fillPath(path, QBrush(self.UNKNOWN_COLOR))
            painter.drawPath(path)
        else:
            painter.setPen(QPen(QColor("#FFc0c0c0")))
            painter.drawRect(rc_out)
        painter.setPen(QPen(self.textInv.getTextColourFromBackground(self.backgroundColor)))
        painter.setFont(QFont("Arial", delta_h*1.8))
        painter.drawText(rc_out, Qt.AlignCenter,  "{}\n{}".format(self._first_line, self._second_line))

        if self._hasIceBelt:
            if self.region_id == current_region_id:
                rc_out = self.rect.__copy__()
                ise_pen = QPen(QColor("#806495ED"))
                ise_pen.setWidthF(2.5)
                painter.setPen(ise_pen)
                painter.setBrush(QBrush(Qt.NoBrush))
                path = QPainterPath()
                path.addRoundedRect(rc_out, 14, 14)
                painter.drawPath(path)

        if self.is_statistics_visible:
            rc_out = self.rect.__copy__()
            rc_out.translate(0.0, rc_out.height())
            rc_out.setHeight(delta_h*2)

            painter.setFont(QFont("Arial", delta_h*1.3))
            painter.setPen(QPen(QColor("#C0FF0000")))
            painter.drawText(rc_out, Qt.AlignCenter, self._svg_text_string)
            painter.setBrush(Qt.NoBrush)

        if self.is_vulnerable_visible:
            rc_out = self.rect.__copy__()
            rc_out.translate(0.0, -delta_h*2)
            rc_out.setHeight(delta_h*2)

            painter.setFont(QFont("Arial", delta_h*1.3))
            painter.setPen(QPen(QColor("#C0FF8000")))
            painter.drawText(rc_out, Qt.AlignCenter, self._vulnerability_text)
            painter.setBrush(Qt.NoBrush)

        self._is_dirty = False

    @property
    def mapCoordinates(self) -> QRectF:
        """
        Gathers the rectangle of the system in map coordinates
        Returns:
            QRectF of the system
        """
        return self.rect

    def applySVG(self, map_coordinates: QRectF) -> None:
        """
        Sets the working rectangle for the system, use x,y,width and height of the dict
        Args:
            map_coordinates:

        Returns:
        """
        self.rect = map_coordinates
        self.center = map_coordinates.center()
        self._is_dirty = True

    def mark(self, sec=10.0):
        """
        Activate the mark for sec seconds
        Args:
            sec:
                marking time, default is 10s
        Returns:

        """
        self.marker = datetime.datetime.utcnow().timestamp() + sec
        self._is_dirty = True

    def addLocatedCharacter(self, char_name, intel_range=None):
        if char_name not in self._locatedCharacters:
            self._locatedCharacters.append(char_name)
            for sys in self.getNeighbours(intel_range):
                sys._isMonitored = sys._isMonitored + 1
            self._is_dirty = True

    def removeLocatedCharacter(self, char_name, intel_range):
        if char_name in self._locatedCharacters:
            self._locatedCharacters.remove(char_name)
            for sys in self.getNeighbours(intel_range):
                if sys._isMonitored > 0:
                    sys._isMonitored = sys._isMonitored - 1
            if self._isMonitored > 0:
                self._isMonitored = self._isMonitored - 1
            self._is_dirty = True

    def changeIntelRange(self, old_intel_range, new_intel_range):
        for char_name in self._locatedCharacters:
            self.removeLocatedCharacter(char_name, old_intel_range)
            self.addLocatedCharacter(char_name, new_intel_range)
            self._is_dirty = True

    def setCampaigns(self, campaigns: bool):
        self._hasCampaigns = campaigns
        self._is_dirty = True

    def setIncursion(self, has_incursion: bool = False, is_staging: bool = False, has_boss: bool = False):
        self._hasIncursion = has_incursion
        self._isStaging = is_staging
        self._hasIncursionBoss = has_boss
        self._is_dirty = True

    def setBackgroundColor(self, color):
        self.backgroundColor = color
        self._is_dirty = True

    def getBackgroundBrush(self) -> QBrush:
        """
        Generates the background brush for the systems, blended from backgroundColor to backgroundColorNext depends
        on the backgroundAlpha
        Returns:

        """
        r = self.backgroundAlpha
        col_a = QColor(self.backgroundColor)
        col_b = QColor(self.backgroundColorNext) if self.backgroundColorNext != "#BACKGD" else self.UNKNOWN_COLOR
        brush_color = QColor(255*(col_b.redF() * (1 - r) + col_a.redF() * r),
                             255*(col_b.greenF() * (1 - r)+col_a.greenF() * r),
                             255*(col_b.blueF() * (1 - r) + col_a.blueF() * r))

        return QBrush(brush_color)

    def getLocatedCharacters(self):
        characters = []
        for char in self._locatedCharacters:
            characters.append(char)
        return characters

    @property
    def neighbours(self):
        """
        Gets the lazy evaluated neighbours systems
        Returns: set[System]
            A set of all Systems with a direct gate connection
        """
        if self._neighbours is None:
            self._neighbours = set()
            for gate in Universe.stargatesBySystemID(self.system_id):
                destination_id = gate["destination"]["system_id"]
                destination_system = ALL_SYSTEMS[destination_id]
                self._neighbours.add(destination_system)
        return self._neighbours

    def getNeighbours(self, distance=1):
        """
            Get all neighboured system with a distance of distance.
            example: sys1 <-> sys2 <-> sys3 <-> sys4 <-> sys5
            sys3(distance=1) will find sys2, sys3, sys4
            sys3(distance=2) will find sys1, sys2, sys3, sys4, sys5
            returns a dictionary with the system (not the system's name!)
            as key and a dict as value. key "distance" contains the distance.
            example:
            {sys3: {"distance"}: 0, sys2: {"distance"}: 1}
        """

        systems = {self: {"distance": 0}}
        current_distance = 0
        while current_distance < distance:
            current_distance += 1
            new_systems = []
            for system in systems.keys():
                for neighbour in system.neighbours:
                    if neighbour not in systems:
                        new_systems.append(neighbour)
            for newSystem in new_systems:
                systems[newSystem] = {"distance": current_distance}
        return systems

    def addKill(self):
        self._hasKill = self._hasKill + 1.0
        self._is_dirty = True

    def setStatus(self, message) -> None:
        """
        Appends a new message to the system
        Args:
            message:

        Returns:
            None
        """
        self._system_messages.append(message)
        self._status = None
        self._is_dirty = True

    def setStatistics(self, statistics: dict) -> None:
        """
        Sets the statistic information as dict, jumps, factionkills, shipkills and podkills will be used as keys
        Args:
            statistics:

        Returns:

        """
        if statistics is None:
            self._svg_text_string = "stats n/a"
        else:
            self._svg_text_string = "j-{jumps} f-{factionkills} s-{shipkills} p-{podkills}".format(**statistics)
        self._is_dirty = True

    def setVulnerabilityInfo(self, sys_sov_structures: dict) -> None:
        """
        Updates the vulnerability information of the system
        Args:
            sys_sov_structures:

        Returns:

        """
        self._vulnerability_text = None
        if "vulnerability_occupancy_level" in sys_sov_structures:
            self.vulnerability_occupancy_level = sys_sov_structures["vulnerability_occupancy_level"]
            self._vulnerability_text = "({})".format(self.vulnerability_occupancy_level )
            self._is_dirty = True

        if "vulnerable_start_time" in sys_sov_structures:
            self.vulnerable_start_time = datetime.datetime.strptime(sys_sov_structures['vulnerable_start_time'],
                                                                  "%Y-%m-%dT%H:%M:%SZ")
            self._vulnerability_text = self._vulnerability_text + " " + self.vulnerable_start_time.strftime("%m/%d %H:%M")
            self._is_dirty = True
        if "vulnerable_end_time" in sys_sov_structures:
            self.vulnerable_end_time = datetime.datetime.strptime(sys_sov_structures['vulnerable_end_time'],
                                                                  "%Y-%m-%dT%H:%M:%SZ")
            self._is_dirty = True

    def updateSystemBackgroundColors(self) -> None:
        """
        Updated the background color depending on the current alarm state and current time
        Returns:
            None
        """
        last_cycle = True
        alarm_time = datetime.datetime.utcnow().timestamp() - self._last_alarm_timestamp
        if self.status == States.ALARM:
            for maxDiff, alarmColour, nextColor, lineColour in self.ALARM_COLORS:
                curr_diff = alarm_time / (Globals().intel_time * 60.0)
                if curr_diff <= maxDiff:
                    self.backgroundAlpha = 1 - alarm_time/(Globals().intel_time*60.0)
                    self.backgroundColor = alarmColour
                    self.backgroundColorNext = nextColor
                    self.statusTextColor = lineColour
                    last_cycle = False
                    break
        elif self.status == States.CLEAR:
            for maxDiff, clearColour, nextColor, lineColour in self.CLEAR_COLORS:
                curr_diff = alarm_time / (Globals().intel_time * 60.0)
                if curr_diff <= maxDiff:
                    self.backgroundAlpha = 1 - alarm_time/(Globals().intel_time*60.0)
                    self.backgroundColor = clearColour
                    self.backgroundColorNext = nextColor
                    self.statusTextColor = lineColour
                    last_cycle = False
                    break

        if self.status in (States.ALARM, States.CLEAR):
            if last_cycle:
                self._second_line_flash = False
                self._second_line = self.ticker
                self.backgroundAlpha = 1.0
                self.backgroundColor = self.UNKNOWN_COLOR
                self.backgroundColorNext = self.UNKNOWN_COLOR
            else:
                minutes = int(math.floor(alarm_time / 60))
                seconds = int(alarm_time - minutes * 60)
                if self._alarm_seconds != seconds:
                    self._alarm_seconds = seconds
                    self._second_line_flash = not self._second_line_flash
                    if self._second_line_flash:
                        self._second_line = "{m:02d}:{s:02d}".format(m=minutes, s=seconds, ticker=self.ticker)
                    else:
                        self._second_line = "{ticker}".format(m=minutes, s=seconds, ticker=self.ticker)
        else:
            self._second_line_flash = False
            if self.vulnerability_occupancy_level:
                self._second_line = "{} ({})".format(self.ticker, self.vulnerability_occupancy_level)
            else:
                self._second_line = self.ticker

            self.backgroundAlpha = 1.0
            self.backgroundColor = self.UNKNOWN_COLOR
            self.backgroundColorNext = self.UNKNOWN_COLOR

    def updateStyle(self):
        for i in range(5):
            self.ALARM_COLORS[i] = (self.ALARM_COLORS[i][0], self.styles.getCommons()["alarm_colours"][i],
                                    self.textInv.getTextColourFromBackground(self.ALARM_COLORS[i][1]))
        self.ALARM_COLOR = self.ALARM_COLORS[0][1]
        self.UNKNOWN_COLOR = self.styles.getCommons()["unknown_colour"]
        self.CLEAR_COLOR = self.styles.getCommons()["clear_colour"]
        self.setBackgroundColor(self.UNKNOWN_COLOR)
        self._is_dirty = True

    def getTooltipText(self):
        if self.vulnerability_occupancy_level:
            format_src = '<span style="font-weight:medium; color:#e5a50a;">{system}</span>' \
                         '<span style="font-weight:medium; font-style:italic; color:#deddda;">&lt;{ticker}&gt;</span>' \
                         '<span style="font-weight:medium; font-style:italic; color:#deddda;">({adm})</span>' \
                         '<br/><span style=" font-weight:medium; color:#e01b24;">{systemstats}</span>'
        else:
            format_src = '<span style="font-weight:medium; color:#e5a50a;">{system}</span>' \
                     '<span style="font-weight:medium; font-style:italic; color:#deddda;">&lt;{ticker}&gt;</span>' \
                     '<br/><span style=" font-weight:medium; color:#e01b24;">{systemstats}</span>'

        # '''<p><span style=" font-weight:bold; color:#deddda;">{timers}</span></p>'''
        # '''<p><span style=" font-weight:bold; color:#deddda;">{zkillinfo}</span></p>'''

        def BR():
            return "<br/>"

        def YELLOW(txt):
            return '''<span style="font-weight:medium; color:#e5a50a;">{}</span>'''.format(txt)

        def GRAY(txt):
            return '''<span style="font-weight:medium; color:#c0c0c0;">{}</span>'''.format(txt)

        def RED(txt):
            return '''<span style="font-weight:medium; color:#e01b24;">{}</span>'''.format(txt)

        if self._hasIncursion:
            if self._isStaging:
                format_src = format_src + '''<br/><span style=" font-weight:medium; color:#ffcc00;">-Incursion Staging{}-</span>'''.format(" Boss" if self._hasIncursionBoss else "")
            else:
                format_src = format_src + '''<br/><span style=" font-weight:medium; color:#ff9900;">-Incursion{}-</span>'''.format(" Boss" if self._hasIncursionBoss else "")

        if bool(self.wormhole_info):
            format_src = format_src + BR() + YELLOW("Wormholes")
            for info in self.wormhole_info:
                region_name = Universe.regionNameFromSystemID(Universe.systemIdByName(info["out_system_name"]))
                format_src = format_src + BR() + "{wh_type} ".format(**info) + \
                    YELLOW("{out_signature} ".format(**info)) + \
                    RED("{out_system_name} ".format(**info)) +  \
                    YELLOW(region_name) + "  " + \
                    RED("({remaining_hours}h {max_ship_size})".format(**info))

        if self._hasCampaigns:
            format_src = format_src + "<br/>Campaigns"
            cache_key = "sovereignty_campaigns"
            response = Cache().getFromCache(cache_key)
            if response:
                campaign_data = json.loads(response)
                for itm in campaign_data:
                    start_time = itm["start_time"]
                    solar_system_id = itm["solar_system_id"]

                    event_type = itm["event_type"]
                    if solar_system_id == self.system_id:
                        if event_type == "tcu_defense":
                            format_src = (format_src + '<br/><span style="font-weight:medium; color:#c00000;">TCU {}</span>'.format(start_time))
                        if event_type == "ihub_defense":
                            format_src = format_src + '<br/><span style="font-weight:medium; color:#c00000;">IHUB {}</span>'.format(start_time)
                        if event_type == "station_defense":
                            format_src = format_src + '<br/><span style="font-weight:medium; color:#c00000;">Defense Events {}</span>'.format(start_time)
                        if event_type == "station_freeport":
                            format_src = format_src + '<br/><span style="font-weight:medium; color:#c00000;">Freeport Events {}</span>'.format(start_time)

        res = format_src.format(
            system=self.name,
            ticker=self.ticker,
            systemstats=self._svg_text_string,
            adm=self.vulnerability_occupancy_level,
            timers="",
            zkillinfo=""
        )

        for msg in self._system_messages:
            time = msg.timestamp.strftime("%H:%M:%S")
            res = res + '<br/>' + GRAY(time) + "-" + msg.guiText
        return res

    def clearIntel(self):
        self._system_messages = []
        self._status = None
        self._is_dirty = True
        self._second_line_flash = False

    def pruneMessage(self, message):
        if message in self._system_messages:
            self._system_messages.remove(message)
            self._status = None


def _InitAllSystemsA():
    for system_id, sys in Universe.SYSTEMS.items():
        Universe.SYSTEMS[system_id]["System"] = System(name=sys["name"], system_id=system_id)
    return Universe.SYSTEMS


def _InitAllSystems():
    res = dict()

    def applyColorToSystem(system_id, tokens):
        if tokens[1][0] == '#' and len(tokens[1]) == 9:
            res[system_id].marking_color = QColor(tokens[1])
        else:
            res[system_id].marking_color = QColor(tokens[1])
            res[system_id].marking_color.setAlphaF(0.3)
        if len(tokens) > 2:
            res[system_id].marking_scale = max(1.0, min(float(tokens[2]), 2.0))

    for system_id, system_data in Universe.SYSTEMS.items():
        res[system_id] = System(name=system_data["name"], system_id=system_id)
    filename = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "backgrounds.txt")
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
            for line in lines:
                if len(line) == 0:
                    continue
                if line[0] is '#':
                    continue
                line = line.split(',')
                if len(line) < 2:
                    continue
                constellation_id = Universe.constellationIdByName(line[0])
                region_id = Universe.regionIdByName(line[0])
                if region_id:
                    region = Universe.regionByID(region_id)
                    for constellation_id in region["constellations"]:
                        constellation = Universe.constellationByID(constellation_id)
                        for system_id in constellation["systems"]:
                            applyColorToSystem(system_id, line)

                if constellation_id:
                    constellation = Universe.constellationByID(constellation_id)
                    for system_id in constellation["systems"]:
                        applyColorToSystem(system_id, line)

                system_id = Universe.systemIdByName(line[0])
                if system_id:
                    applyColorToSystem(system_id, line)

    return res


ALL_SYSTEMS = _InitAllSystems()
