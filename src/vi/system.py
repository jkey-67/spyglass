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
import logging
###########################################################################
# Little lib and tool to get the map and information from dotlan		  #
###########################################################################
import json
import os
import time
import datetime
from typing import Optional

from PySide6.QtCore import QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor
from vi.states import States
from vi.cache import Cache
from vi.ui.styles import Styles, TextInverter
from vi.universe import Universe, Position, Stargate
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
            Ticker of the alliance holding the sovereignty

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

    # structure type_id sorted by size
    M_SIZE = [35832, 35825, 35826, 35835, 35836]
    L_SIZE = [35833, 47512, 47513, 47514, 47515, 47516, 35827]
    XL_SIZE = [35834, 40340]

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

    def __init__(self, **kwargs):
        self.system_id:int = kwargs["system_id"]
        self.name:str = kwargs["names"]["en"]
        self.names:dict = kwargs["names"]
        self.constellation_id = kwargs["constellation_id"]
        self.constellation_name: str = Universe.CONSTELLATIONS_ID_OBJS.get(self.constellation_id).name
        self.region_id:int = kwargs["region_id"]
        self.region_name:str = Universe.REGIONS_ID_OBJ.get(self.region_id).name
        self.planets:list[int] = kwargs["planets"]
        self.position2D:Position = Position(**kwargs["position2D"])
        self.position3D: Position = Position(**kwargs["position"])
        self.security_class:str = kwargs["security_class"]
        self.security_status:float = kwargs["security_status"]
        self.star_id: Optional[int] = kwargs["star_ID"] if "star_ID" in kwargs else None
        self.stargates:list[int] = kwargs["stargates"]
        self.stations:list[int] = []
        self.structures:list[dict] = []
        self.ticker:str = "-?-"
        self._system_messages = []
        self.jumpBridges:set = set()
        self.theraWormholes:set = set()
        self.backgroundAlpha:float = 1.0
        self.backgroundColor = self.UNKNOWN_COLOR
        self.backgroundColorNext = self.UNKNOWN_COLOR
        self.statusTextColor = "#FFFFFF"
        self.marker_start = 0.0
        self.marker_end = 0.0
        self.wormhole_info = list()
        self.alarm_distance = set()
        self.rect = QRectF(0,0,System.ELEMENT_WIDTH,System.ELEMENT_HEIGHT)
        self.is_ice_belts_visible = True
        self.is_structure_visible = True
        self.is_vulnerable_visible = True
        self.is_statistics_visible = True
        self.is_jumpbridges_visible = True
        self.is_system_text_visible = True
        self.render_out_of_region = True
        self._is_dirty = True
        self._status = None
        self._first_line = self.name
        self._second_line = self.ticker
        self.intel_start = 0.0
        self.intel_end = 0.0
        self.locatedCharacters = []
        self._neighbours = None
        self.hasCampaigns = False
        self.hasIncursion = False
        self.has_ice_belt = False
        self.isIncursionStaging = False
        self.incursionState = ""
        self.incursionInfluence = 0.0
        self.hasIncursionBoss = False
        self._hasThera = False
        self._monitoredDistance = []
        self.kill_start = 0.0
        self.kill_end = 0.0
        self._svg_text_string = "stats n/a"
        self._alarm_seconds = 0
        self._structure_type = None
        self.vulnerability_occupancy_level = None
        self.vulnerable_end_time = None
        self.vulnerable_start_time = None
        self._vulnerability_text = None
        self.marking_color = None
        self.marking_scale = 1.0
        self.has_upwell_cyno_jammer = False
        self.has_upwell_cyno_beacon = False

    def out_rect(self)->QRectF:
        if self.is_system_text_visible:
            return self.rect.__copy__()
        else:
            return QRectF(self.rect.center()-QPointF(6,6), self.rect.center()+QPointF(6,6))

    def isMonitored(self) -> bool:
        return bool(self._monitoredDistance)

    @property
    def x(self)->float:
        if Position.USE_3D:
            return self.position3D.x * Position.GL_MAP_FACTOR_3D
        else:
            return self.position2D.x * Position.GL_MAP_FACTOR_2D

    @property
    def y(self)->float:
        if Position.USE_3D:
            return self.position3D.y * Position.GL_MAP_FACTOR_3D
        else:
            return self.position2D.y * Position.GL_MAP_FACTOR_2D

    @property
    def z(self)->float:
        if Position.USE_3D:
            return self.position3D.z * Position.GL_MAP_FACTOR_3D
        else:
            return self.position2D.z * Position.GL_MAP_FACTOR_2D

    @property
    def structure(self)->int:
        return 0

    @property
    def intel_status(self) -> int:
        status = self.status
        if status == States.ALARM:
            return 2 # red
        elif status == States.CLEAR:
            return 1 # green
        else:
            return 0 # none

    @property
    def hasKill(self)->float:
        return self.kill_end


    @intel_status.setter
    def intel_status(self,val) -> None:
        self._status = None

    @property
    def intel_status_time(self) -> float:
        return self.intel_end

    def intel_status_time_string(self,now) -> str:
        if self.intel_end > self.intel_start:
            if now < self.intel_end:
                age = max(0.0, now - self.intel_start)
                # swap in between ticker and time
                if  bool(int(age) % 2):
                    minutes = int(age // 60.0)
                    seconds = int(age % 60.0)
                    return f"{minutes:02d}:{seconds:02d}"
                else:
                    return self.ticker
        self._status = None
        self.intel_start = 0.0
        self.intel_end = 0.0
        return self.ticker

    @intel_status_time.setter
    def intel_status_time(self,val):
        pass


    @property
    def monitoredRange(self) -> int:
        if self.isMonitored():
            return min(self._monitoredDistance)
        else:
            return 10

    @property
    def center(self) -> QPointF:
        return self.rect.center()

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    def clr_dirty(self):
        self._is_dirty = False

    @property
    def sec_state(self)->str:
        return "{:.2f} {}".format(self.security_status, self.security_class)

    @property
    def timer(self)->str:
        if self._vulnerability_text is None:
            return ""
        else:
            return self._vulnerability_text

    @property
    def statistics(self)->str:
        return self._svg_text_string



    @property
    def status(self):
        """
        Laze evaluated status for the system, background and second line flash is adjusted.
        Returns:
            The status of the system States.UNKNOWN, States.ALARM or States.CLEAR
        """
        if self._status is None:
            if len(self._system_messages):
                cfg = Globals()
                msg = self._system_messages[-1]
                self.intel_start = msg.timestamp.timestamp()
                self.intel_end = msg.timestamp.timestamp() + cfg.intel_time * 60.0
                self._status = msg.status
            else:
                self._status = States.UNKNOWN
            if self._status == States.ALARM:
                self.setBackgroundColor(self.ALARM_COLOR)
            elif self._status == States.CLEAR:
                self.setBackgroundColor(self.CLEAR_COLOR)
            elif self._status == States.UNKNOWN:
                self.setBackgroundColor(System.UNKNOWN_COLOR)
                self.intel_start = 0.0
                self.intel_end = 0.0
        return self._status

    @property
    def structure_type(self):
        if self._structure_type is None:
            self._structure_type = 0
            for struct in self.structures:
                if "type_id" in struct:
                    if struct["type_id"] in System.XL_SIZE:
                        self._structure_type = max(3, self._structure_type)
                    elif struct["type_id"] in System.L_SIZE:
                        self._structure_type = max(2, self._structure_type)
                    elif struct["type_id"] in System.M_SIZE:
                        self._structure_type = max(1, self._structure_type)
            return self._structure_type
        else:
            return self._structure_type

    @staticmethod
    def structurePen():
        border_pen = QPen(QColor("#FFC0C0C0"))
        border_pen.setWidthF(0.3)
        return border_pen

    @staticmethod
    def structureBrush():
        return QBrush(QColor(System.UNKNOWN_COLOR))

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
        self._is_dirty = True

    def markSystem(self, now:float=time.time(), duration:float=10.0):
        """
        Activate the mark for sec seconds
        Args:
            now:
                start time
            duration:
                marking time, default is 10s
        Returns:

        """
        self.marker_start = now
        self.marker_end = now + duration
        self._is_dirty = True

    def _addLocatedCharacter(self, distance:int):
        self._monitoredDistance.append(distance)
        self._is_dirty = True

    def _removeLocatedCharacter(self, distance:int):
        if distance in self._monitoredDistance:
            self._monitoredDistance.remove(distance)
        self._is_dirty = True

    def addLocatedCharacter(self, char_name, intel_range=None):
        if char_name not in self.locatedCharacters:
            self.locatedCharacters.append(char_name)
            self._addLocatedCharacter(0)
            self.getNeighbors(intel_range, System._addLocatedCharacter)


    def removeLocatedCharacter(self, char_name, intel_range):
        if char_name in self.locatedCharacters:
            self.locatedCharacters.remove(char_name)
            self._removeLocatedCharacter(0)
            self.getNeighbors(intel_range, System._removeLocatedCharacter)

    def changeIntelRange(self, old_intel_range, new_intel_range):
        for char_name in self.locatedCharacters:
            self.removeLocatedCharacter(char_name, old_intel_range)
            self.addLocatedCharacter(char_name, new_intel_range)
            self._is_dirty = True

    def setCampaigns(self, campaigns: bool):
        self.hasCampaigns = campaigns
        self._is_dirty = True

    def setIncursion(self, has_incursion: bool = False, is_staging: bool = False, has_boss: bool = False, state:str="",influence:float=0.0,):
        self.hasIncursion = has_incursion
        self.isIncursionStaging = is_staging
        self.hasIncursionBoss = has_boss
        self.incursionState = state
        self.incursionInfluence = influence
        self._is_dirty = True

    def setBackgroundColor(self, color):
        self.backgroundColor = color
        # self._is_dirty = True

    def getLocatedCharacters(self):
        characters = []
        for char in self.locatedCharacters:
            characters.append(char)
        return characters

    @property
    def neighbors(self):
        """
        Gets the lazy evaluated neighbors systems
        Returns: set[System]
            A set of all Systems with a direct gate connection
        """
        if self._neighbours is None:
            self._neighbours = set()
            for gate in Universe.stargatesBySystemID(self.system_id):
                destination_id = gate.destination.system_id
                destination_system = ALL_SYSTEMS[destination_id]
                self._neighbours.add(destination_system)
        return self._neighbours

    def getNeighbors(self, distance=1, fnc_distance=None):
        """
            Get all neighbors system with a distance of distance.
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
                for neighbour in system.neighbors:
                    if neighbour not in systems:
                        new_systems.append(neighbour)
            for newSystem in new_systems:
                if fnc_distance:
                    fnc_distance(newSystem, current_distance)
                systems[newSystem] = {"distance": current_distance}

        return systems

    def addKill(self,utc_time,delta:float=60.0):
        self.kill_start = utc_time
        self.kill_end = utc_time + delta
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
        if "vulnerability_occupancy_level" in sys_sov_structures:
            self.vulnerability_occupancy_level = sys_sov_structures["vulnerability_occupancy_level"]
            self._vulnerability_text = "({})".format(self.vulnerability_occupancy_level)
        else:
            self.vulnerability_occupancy_level = None
            self._vulnerability_text = ""

        if "vulnerable_start_time" in sys_sov_structures:
            self.vulnerable_start_time = datetime.datetime.strptime(sys_sov_structures['vulnerable_start_time'],
                                                                  "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            self._vulnerability_text = (self.vulnerable_start_time.strftime("%m/%d %H:%M") + " " +
                                        self._vulnerability_text)
        else:
            self.vulnerable_start_time = None

        if "vulnerable_end_time" in sys_sov_structures:
            self.vulnerable_end_time = datetime.datetime.strptime(sys_sov_structures['vulnerable_end_time'],
                                                                  "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        else:
            self.vulnerable_end_time = None

        self._is_dirty = True

    def updateStyle(self):
        """
        for i in range(5):
            self.ALARM_COLORS[i] = (self.ALARM_COLORS[i][0], System.styles.getCommons()["alarm_colours"][i],
                                    self.textInv.getTextColourFromBackground(self.ALARM_COLORS[i][1]))
        self.ALARM_COLOR = self.ALARM_COLORS[0][1]
        """
        System.UNKNOWN_COLOR = System.styles.getCommons()["unknown_colour"]
        self.CLEAR_COLOR = System.styles.getCommons()["clear_colour"]
        self.setBackgroundColor(System.UNKNOWN_COLOR)
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

        if self.hasIncursion:
            if self.isIncursionStaging:
                format_src = format_src + '''<br/><span style=" font-weight:medium; color:#ffcc00;">-Incursion Staging{}-</span>'''.format(" Boss" if self.hasIncursionBoss else "")
            else:
                format_src = format_src + '''<br/><span style=" font-weight:medium; color:#ff9900;">-Incursion{}-</span>'''.format(" Boss" if self.hasIncursionBoss else "")

        if bool(self.wormhole_info):
            format_src = format_src + BR() + YELLOW("Wormholes")
            for info in self.wormhole_info:
                region_name = Universe.regionNameFromSystemID(Universe.systemIdByName(info["out_system_name"]))
                format_src = format_src + BR() + "{wh_type} ".format(**info) + \
                    YELLOW("{out_signature} ".format(**info)) + \
                    RED("{out_system_name} ".format(**info)) +  \
                    YELLOW(region_name) + "  " + \
                    RED("({remaining_hours}h {max_ship_size})".format(**info))

        if self.hasCampaigns:
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
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            res = res + '<br/>' + GRAY(timestamp) + "-" + msg.guiText
        return res

    def clearIntel(self):
        self._system_messages = []
        self._status = None
        self.intel_start = self.intel_end = self.kill_end = self.marker_start = self.marker_end = 0.0
        self._is_dirty = True

    def pruneMessage(self, message):
        if message in self._system_messages:
            self._system_messages.remove(message)
            self._status = None


def _ApplyColorToSystem(data:dict[int, System]()):
    """
        Importing the SMT InfoObjects.txt file to add backgrounds to the systems
    Args:
        data: dict[systemId, System]()

    Returns:

    """
    line_no = 0
    offs_rgn_name = 1
    offs_id = 2
    offs_width = 3
    offs_color = 4

    def applyColorToSystem(systemid, tokens):
        if tokens[offs_rgn_name][0] == '#' and len(tokens[offs_color]) == 9:
            data[systemid].marking_color = QColor(tokens[offs_color])
        else:
            data[systemid].marking_color = QColor(tokens[offs_color])
            data[systemid].marking_color.setAlphaF(0.3)
        if len(tokens) > offs_color:
            data[systemid].marking_scale = max(1.0, min(float(tokens[offs_width])/24.0, 2.0))

    filename = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "InfoObjects.txt")
    if os.path.exists(filename):
        logging.info("Parse color backgrounds from {}".format(filename))
        with open(filename, "r", encoding="utf-8") as f:
            current_line = ""
            try:
                content = f.read()
                lines = content.split("\n")
                for current_line in lines:
                    line_no += 1
                    if len(current_line) == 0:
                        continue
                    if current_line.startswith('#'):
                        continue
                    line_split = current_line.split(',')
                    if len(line_split) <= offs_color:
                        logging.error("Invalid line systax in file : {} line : {} '{}'".format(filename, line_no, current_line))
                        continue
                    constellation_id = Universe.constellationIdByName(line_split[offs_id])
                    region_id = Universe.regionIdByName(line_split[offs_id])
                    if region_id:
                        region = Universe.regionByID(region_id)
                        for constellation_id in region.constellations:
                            constellation = Universe.constellationByID(constellation_id)
                            for system_id in constellation.systems:
                                applyColorToSystem(system_id, line_split)

                    if constellation_id:
                        constellation = Universe.constellationByID(constellation_id)
                        for system_id in constellation.systems:
                            applyColorToSystem(system_id, line_split)

                    system_id = Universe.systemIdByName(line_split[offs_id])
                    if system_id:
                        applyColorToSystem(system_id, line_split)
            except (Exception,)as _:
                logging.error("Invalid line systax in file : {} line : {} '{}'".format(filename, line_no, current_line))

def _ApplyIceToSystem(data):
    def applyIceToSystem(system_id, tokens):
        if len(tokens):
            data[system_id].has_ice_belt = True

    filename = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "IceSystems.txt")

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            line_no = 0
            current_line = ""
            try:
                content = f.read()
                lines = content.split("\n")
                for current_line in lines:
                    line_no += 1
                    if len(current_line) == 0:
                        continue
                    if current_line.startswith('#'):
                        continue
                    line = current_line.split(',')
                    if len(line) == 0:
                        continue
                    system_id = Universe.systemIdByName(line[0])
                    if system_id:
                        applyIceToSystem(system_id, line)
            except (Exception,) as _:
                logging.error("Invalid line systax in file : {} line : {} '{}'".format(filename, line_no, current_line))

def _applyStructuresToSystem(data, system_id_app, tokens):
    if len(tokens) > 2:
        new_data = {"type_id": int(tokens[0]), "structure_id": int(tokens[1]), "name": tokens[3]}
        type_id = int(tokens[0])
        if type_id in list(set().union(System.M_SIZE, System.L_SIZE, System.XL_SIZE)):
            if data[system_id_app].structures is None:
                data[system_id_app].structures = [new_data]
            else:
                data[system_id_app].structures.append(new_data)
        elif type_id == 2017:
            data[system_id_app].has_cyno_beacon = True


def _ApplyStructuresToSystem(data):

    filename = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "spyglass", "Structures.txt")

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                content = f.read()
                lines = content.split("\n")
                for line in lines:
                    if len(line) == 0:
                        continue
                    if line.startswith('#'):
                        continue
                    line = line.split(',')
                    if len(line) < 2:
                        continue
                    system_id = Universe.systemIdByName(line[2])
                    if system_id:
                        _applyStructuresToSystem(data, system_id, line)
            except (Exception,)as _:
                pass

def _InitAllSystems() -> dict[int, System]:
    res = dict[int, System]()
    for system_id, system_data in Universe.SYSTEMS.items():
        res[system_id] = System(**system_data)

    _ApplyColorToSystem(res)
    _ApplyIceToSystem(res)
    _ApplyStructuresToSystem(res)
    return res

def _InitAllStargates() -> dict[int, Stargate]:
    res = dict[int, Stargate]()
    for _id, _data in Universe.STARGATES.items():
        res[_id] = Stargate(_id,**_data)
    return res


ALL_SYSTEMS = _InitAllSystems()
ALL_STARGATES = _InitAllStargates()