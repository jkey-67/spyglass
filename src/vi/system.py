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

from PySide6.QtCore import QRectF, QPointF, Qt, QMargins, QLineF
from PySide6.QtGui import QPainter, QFont, QPen, QBrush, QColor, QRadialGradient, QPainterPath
from vi.states import States
from vi.cache.cache import Cache
from vi.ui.styles import Styles, TextInverter
from vi.universe import Universe


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

    ALARM_BASE_T = 60  # set 1 for testing
    ALARM_COLORS = [(ALARM_BASE_T * 5,  "#d00000", "#FFFFFF"),
                    (ALARM_BASE_T * 10, "#D09B0F", "#FFFFFF"),
                    (ALARM_BASE_T * 15, "#D0FA0F", "#000000"),
                    (ALARM_BASE_T * 20, "#D0FDA2", "#000000"),
                    (0,       "#FFFFFF", "#000000")]

    CLEAR_COLORS = [(ALARM_BASE_T * 5,  "#00FF00", "#000000"),
                    (ALARM_BASE_T * 10, "#40FF40", "#000000"),
                    (ALARM_BASE_T * 15, "#80FF80", "#000000"),
                    (ALARM_BASE_T * 20, "#C0FFC0", "#000000"),
                    (0,       "#FFFFFF", "#000000")]

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
        self.backgroundColor = self.UNKNOWN_COLOR
        self.center = QPointF()
        self.rect = QRectF(0.0, 0.0, 64.0, 32.0)
        self.marker = 0.0
        self.wormhole_info = list()

        self.is_statistics_visible = True
        self.is_jumpbridges_visible = True

        self.is_mark_dirty = False
        self.is_background_dirty = True
        self.is_incursion_dirty = True
        self.is_status_dirty = True
        self.is_campaign_dirty = True
        self.is_statistic_dirty = True
        self.is_located_char_dirty = False

        self._status = None
        self._first_line = self.name
        self._second_line = ""
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
        self._svg_text_string = "stats n/a"
        self._alarm_seconds = 0

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
            if system.name in systems.keys():
                if self.region_id == current_region_id:
                    if self.constellation_id == system.constellation_id:
                        painter.setPen(QColor("#80ffd700"))
                    else:
                        painter.setPen(QColor("#80ffd700"))
                else:
                    painter.setPen(QColor("#80ffd700"))
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
                painter.setPen(QColor("#80ffd700"))
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
            path.addRoundedRect(rc_out_back.x(), rc_out_back.y(), rc_out_back.width(), rc_out_back.height(), delta_h, delta_h)

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
            path.addRoundedRect(rc_out_back.x(), rc_out_back.y(), rc_out_back.width(), rc_out_back.height(), delta_h, delta_h)
            for i in range(int(-delta_w), int(delta_w), 5):
                gradient.setCenter(rc_out_back.center().x()+i, rc_out_back.center().y())
                painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)
        if bool(self._locatedCharacters):
            gradient = QRadialGradient(self.rect.center(), self.ELEMENT_WIDTH)
            gradient.setColorAt(0.0, QColor("#30800080"))
            gradient.setColorAt(0.6, QColor("#00800080"))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(rc_out_back.x(), rc_out_back.y(), rc_out_back.width(), rc_out_back.height(), delta_h, delta_h)
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
            path.addEllipse(rc_out_back.x(), rc_out_back.y(), rc_out_back.width(), rc_out_back.height())
            gradient.setCenter(rc_out_back.center().x(), rc_out_back.center().y())
            painter.fillPath(path, QBrush(gradient))
            painter.drawPath(path)
            painter.setBrush(Qt.NoBrush)

    def renderSystem(self, painter: QPainter, current_region_id):
        """
        Renders the system to a painter
        Args:
            painter: QPainter to use
            current_region_id: region id of map

        Returns:

        """
        delta_h = self.ELEMENT_HEIGHT / 8
        rc_out = self.rect.__copy__().marginsAdded(QMargins(-2, -2, -2, -2))
        painter.setBrush(QBrush(self.backgroundColor))
        if self.region_id == current_region_id:
            painter.setPen(QPen(QColor("#FFc0c0c0")))
            path = QPainterPath()
            path.addRoundedRect(rc_out, 12, 12)
            painter.fillPath(path, QBrush(self.UNKNOWN_COLOR))
            painter.drawPath(path)
        else:
            painter.setPen(QPen(QColor("#c71585")))
            painter.drawRect(rc_out)
        painter.setPen(QPen(self.textInv.getTextColourFromBackground(self.backgroundColor)))
        painter.setFont(QFont("Arial", delta_h*2))
        painter.drawText(rc_out, Qt.AlignCenter,  "{}\n{}".format(self._first_line, self._second_line))

        if self.is_statistics_visible:
            rc_out.translate(0.0, rc_out.height())
            rc_out.setHeight(delta_h*2)

            painter.setFont(QFont("Arial", delta_h*1.5))
            painter.setPen(QPen(QColor("#80FF0000")))
            painter.drawText(rc_out, Qt.AlignCenter, self._svg_text_string)
            painter.setBrush(Qt.NoBrush)

    @property
    def mapCoordinates(self) -> QRectF:
        """
        Gathers the rectangle of the system in map coordinates
        Returns:
            QRectF of the system
        """
        return self.rect

    @property
    def is_dirty(self):
        """
        Gathers the dirty flag of the system, a request to be repainted
        Returns:

        """
        return self.is_mark_dirty or self.is_background_dirty or self.is_incursion_dirty or self.is_status_dirty \
            or self.is_campaign_dirty or self.is_statistic_dirty or self.is_located_char_dirty or self._second_line_flash

    def applySVG(self, map_coordinates: dict, scale: float = 1228./1024.):
        """
        Sets the working rectangle for the system, use x,y,width and height of the dict
        Args:
            map_coordinates:
            scale:
                Scaling factor for the distance in between the systems base on 1027x768 DotLan SVG Maps, the default is 1.2

        Returns:

        """
        self.rect = QRectF(map_coordinates["x"]*scale,
                           map_coordinates["y"]*scale,
                           map_coordinates["width"],
                           map_coordinates["height"])
        self.center = self.rect.center()

    def mark(self):
        self.is_mark_dirty = True
        self.marker = datetime.datetime.utcnow().timestamp() + 10.0

    def addLocatedCharacter(self, char_name):
        if char_name not in self._locatedCharacters:
            self._locatedCharacters.append(char_name)

    def setCampaigns(self, campaigns: bool):
        self.is_campaign_dirty = True
        self._hasCampaigns = campaigns

    def setIncursion(self, has_incursion: bool = False, is_staging: bool = False, has_boss: bool = False):
        self.is_incursion_dirty = True
        self._hasIncursion = has_incursion
        self._isStaging = is_staging
        self._hasIncursionBoss = has_boss

    def setBackgroundColor(self, color):
        self.is_background_dirty = True
        self.backgroundColor = color

    def getLocatedCharacters(self):
        characters = []
        for char in self._locatedCharacters:
            characters.append(char)
        return characters

    def removeLocatedCharacter(self, char_name):
        if char_name in self._locatedCharacters:
            self._locatedCharacters.remove(char_name)

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
        self.is_status_dirty = True

    def setStatistics(self, statistics : dict) -> None:
        """
        Sets the statistic information as dict, jumps, factionkills, shipkills and podkills will be used as keys
        Args:
            statistics:

        Returns:

        """
        self.is_statistic_dirty = True
        if statistics is None:
            self._svg_text_string = "stats n/a"
        else:
            self._svg_text_string = "j-{jumps} f-{factionkills} s-{shipkills} p-{podkills}".format(**statistics)

    def updateSVG(self):
        last_cycle = True
        alarm_time = datetime.datetime.utcnow().timestamp() - self._last_alarm_timestamp
        if self.status == States.ALARM:
            for maxDiff, alarmColour, lineColour in self.ALARM_COLORS:
                if alarm_time < maxDiff:
                    self.backgroundColor = alarmColour
                    last_cycle = False
                    break
        elif self.status == States.CLEAR:
            for maxDiff, clearColour, lineColour in self.CLEAR_COLORS:
                if alarm_time < maxDiff:
                    self.backgroundColor = clearColour
                    last_cycle = False
                    break

        if self.status in (States.ALARM, States.CLEAR):
            if last_cycle:
                self._second_line_flash = False
                self.backgroundColor = self.UNKNOWN_COLOR

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
            self._second_line =self.ticker

    def updateStyle(self):
        for i in range(5):
            self.ALARM_COLORS[i] = (self.ALARM_COLORS[i][0], self.styles.getCommons()["alarm_colours"][i],
                                    self.textInv.getTextColourFromBackground(self.ALARM_COLORS[i][1]))
        self.ALARM_COLOR = self.ALARM_COLORS[0][1]
        self.UNKNOWN_COLOR = self.styles.getCommons()["unknown_colour"]
        self.CLEAR_COLOR = self.styles.getCommons()["clear_colour"]
        self.setBackgroundColor(self.UNKNOWN_COLOR)

    def getTooltipText(self):
        format_src = '''<span style=" font-weight:600; color:#e5a50a;">{system}</span>''' \
                     '''<span style=" font-weight:600; font-style:italic; color:#deddda;">&lt;{ticker}&gt;</span>''' \
                     '''<br/><span style=" font-weight:600; color:#e01b24;">{systemstats}</span>'''

        # '''<p><span style=" font-weight:600; color:#deddda;">{timers}</span></p>'''
        # '''<p><span style=" font-weight:600; color:#deddda;">{zkillinfo}</span></p>'''

        if self._hasIncursion:
            if self._isStaging:
                format_src = format_src + '''<br/><span style=" font-weight:600; color:#ffcc00;">-Incursion Staging{}-</span>'''.format(" Boss" if self._hasIncursionBoss else "")
            else:
                format_src = format_src + '''<br/><span style=" font-weight:600; color:#ff9900;">-Incursion{}-</span>'''.format(" Boss" if self._hasIncursionBoss else "")

        if self._hasCampaigns:
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
                            format_src = (format_src + '<br/><span style=" font-weight:600; color:#c00000;">TCU {}</span>'.format(start_time))
                        if event_type == "ihub_defense":
                            format_src = format_src + '<br/><span style=" font-weight:600; color:#c00000;">IHUB {}</span>'.format(start_time)
                        if event_type == "station_defense":
                            format_src = format_src + '<br/><span style=" font-weight:600; color:#c00000;">Defense Events {}</span>'.format(start_time)
                        if event_type == "station_freeport":
                            format_src = format_src + '<br/><span style=" font-weight:600; color:#c00000;">Freeport Events {}</span>'.format(start_time)

        res = format_src.format(
            system=self.name,
            ticker=self.ticker,
            systemstats=self._svg_text_string,
            timers="",
            zkillinfo=""
        )

        for msg in self._system_messages:
            res = res + "<br/>" + msg.guiText
        return res

    def clearIntel(self):
        self._system_messages.clear()
        self._status = None

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
    for system_id, system_data in Universe.SYSTEMS.items():
        res[system_id] = System(name=system_data["name"], system_id=system_id)
    return res


ALL_SYSTEMS = _InitAllSystems()

