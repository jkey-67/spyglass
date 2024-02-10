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
import logging
import json

from vi.states import States
from vi.cache.cache import Cache
from vi.ui.styles import Styles, TextInverter


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
        self.__alarmDistances = set()
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
    ALARM_COLORS = [(ALARM_BASE_T * 5,  "#FF0000", "#FFFFFF"),
                    (ALARM_BASE_T * 10, "#FF9B0F", "#FFFFFF"),
                    (ALARM_BASE_T * 15, "#FFFA0F", "#000000"),
                    (ALARM_BASE_T * 20, "#FFFDA2", "#000000"),
                    (0,       "#FFFFFF", "#000000")]

    CLEAR_COLORS = [(ALARM_BASE_T * 5,  "#00FF00", "#000000"),
                    (ALARM_BASE_T * 10, "#40FF40", "#000000"),
                    (ALARM_BASE_T * 15, "#80FF80", "#000000"),
                    (ALARM_BASE_T * 20, "#C0FFC0", "#000000"),
                    (0,       "#FFFFFF", "#000000")]

    ALARM_COLOR = ALARM_COLORS[0][1]
    UNKNOWN_COLOR = styles.getCommons()["unknown_colour"]
    CLEAR_COLOR = CLEAR_COLORS[0][1]

    def __init__(self, name, svg_element, map_soup, map_coordinates, transform, system_id, ticker="-?-"):
        self.status = States.UNKNOWN
        self.name = name
        self.systemId = system_id
        self.ticker = ticker
        self.messages = []
        self._svg_element = None
        self._map_soup = None
        self._rect = None
        self._first_line = None
        self._second_line = None
        self._second_line_flash = False
        self._last_alarm_timestamp = 0
        self._locatedCharacters = []
        self.backgroundColor = self.styles.getCommons()["bg_colour"]
        self._map_coordinates = None
        self._transform = "translate(0, 0)" if transform is None else transform
        self._cachedOffsetPoint = None
        self._neighbours = set()
        self._alarmDistances = set()
        # self.statistics = {"jumps": "?", "shipkills": "?", "factionkills": "?", "podkills": "?"}
        self._currentStyle = ""
        self._hasCampaigns = False
        self._hasIncursion = False
        self._isStaging = False
        self._hasIncursionBoss = False
        self._svg_text = None
        self.applySVG(svg_element, map_soup, map_coordinates, transform)

    @property
    def mapCoordinates(self):
        return self._map_coordinates

    def applySVG(self, svg_element, map_soup, map_coordinates, transform):
        self._svg_element = svg_element
        self._map_soup = map_soup
        self._map_coordinates = map_coordinates
        self._rect = svg_element.select("rect")[0]
        self._first_line = svg_element.select("text")[0]
        self._second_line = svg_element.select("text")[1]
        self._second_line_flash = False
        self._last_alarm_timestamp = 0
        self._transform = "translate(0, 0)" if transform is None else transform
        self._neighbours = set()
        self._alarmDistances = set()
        self.setStatus(self.status)

    def getTransformOffsetPoint(self):
        if not self._cachedOffsetPoint:
            if self._transform:
                # Convert data in the form 'transform(0,0)' to a list of two floats
                point_string = self._transform[9:].strip('()').split(',')
                self._cachedOffsetPoint = [float(point_string[0]), float(point_string[1])]
            else:
                self._cachedOffsetPoint = [0.0, 0.0]
        return self._cachedOffsetPoint

    def mark(self):
        marker = self._map_soup.select("#select_marker")[0]
        offset_point = self.getTransformOffsetPoint()
        x = self._map_coordinates["center_x"] + offset_point[0]
        y = self._map_coordinates["center_y"] + offset_point[1]
        marker["transform"] = "translate({x},{y})".format(x=x, y=y)
        marker["opacity"] = "1.0"
        marker["activated"] = datetime.datetime.utcnow().timestamp()

    def addLocatedCharacter(self, char_name):
        id_name = self.name + u"_loc"
        was_located = bool(self._locatedCharacters)
        if char_name not in self._locatedCharacters:
            self._locatedCharacters.append(char_name)
        if not was_located:
            coordinates = self._map_coordinates
            new_tag = self._map_soup.new_tag(
                "rect", x=coordinates["x"]-10, y=coordinates["y"]-8,
                width=coordinates["width"]+16, height=coordinates["height"]+16, id=id_name,
                rx=12, ry=12, fill="url(#grad_located)")
            jumps = self._map_soup.select("#jumps")[0]
            jumps.insert(0, new_tag)

    def setCampaigns(self, campaigns: bool):
        id_name = self.name + u"_campaigns"
        if campaigns and not self._hasCampaigns:
            camp_node = self._map_soup.find(id=id_name)
            if camp_node is None:
                coordinates = self._map_coordinates
                new_tag = self._map_soup.new_tag(
                    "rect", x=coordinates["x"]-10, y=coordinates["y"]-8,
                    width=coordinates["width"]+16, height=coordinates["height"]+16, id=id_name,
                    rx=12, ry=12, fill="url(#camActiveBg)")
                jumps = self._map_soup.select("#jumps")[0]
                jumps.insert(0, new_tag)
        elif not campaigns and self._hasCampaigns:
            camp_node = self._map_soup.find(id=id_name)
            camp_node.decompose()
        self._hasCampaigns = campaigns

    def setIncursion(self, has_incursion: bool = False, is_staging: bool = False, has_boss: bool = False):
        id_name = self.name + u"_incursion"
        if has_incursion and not self._hasIncursion:
            curr_node = self._map_soup.find(id=id_name)
            if curr_node is None:
                coords = self._map_coordinates
                new_tag = self._map_soup.new_tag("rect", x=coords["x"] - 10, y=coords["y"] - 8, width=coords["width"] + 16,
                                                 height=coords["height"]+16, id=id_name, rx=12, ry=12,
                                                 fill="url(#incStBg)" if has_boss else "url(#incBg)")
                jumps = self._map_soup.select("#jumps")[0]
                jumps.insert(0, new_tag)
        elif not has_incursion and self._hasIncursion:
            camp_node = self._map_soup.find(id=id_name)
            camp_node.decompose()
        self._hasIncursion = has_incursion
        self._isStaging = is_staging
        self._hasIncursionBoss = has_boss

    def setBackgroundColor(self, color):
        for rect in self._svg_element("rect"):
            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                rect["style"] = "fill: {0};".format(color)
        self.backgroundColor = color

    def getLocatedCharacters(self):
        characters = []
        for char in self._locatedCharacters:
            characters.append(char)
        return characters

    def removeLocatedCharacter(self, charname):
        id_name = self.name + u"_loc"
        if charname in self._locatedCharacters:
            self._locatedCharacters.remove(charname)
            if not self._locatedCharacters:
                try:
                    elem = self._map_soup.find(id=id_name)
                    if elem is not None:
                        logging.debug("removeLocatedCharacter {0} Decompose {1}".format(charname, str(elem)))
                        elem.decompose()
                except Exception as e:
                    logging.critical("Error in removeLocatedCharacter  {0}".format(str(e)))
                    pass

    def addNeighbour(self, neighbour_system):
        """
            Add a neighbour system to this system
            neighbour_system: a system (not a system's name!)
        Args:
            neighbour_system(System):
        """
        self._neighbours.add(neighbour_system)
        neighbour_system._neighbours.add(self)

    def getNeighbours(self, distance=1):
        """
            Get all neigboured system with a distance of distance.
            example: sys1 <-> sys2 <-> sys3 <-> sys4 <-> sys5
            sys3(distance=1) will find sys2, sys3, sys4
            sys3(distance=2) will find sys1, sys2, sys3, sys4, sys5
            returns a dictionary with the system (not the system's name!)
            as key and a dict as value. key "distance" contains the distance.
            example:
            {sys3: {"distance"}: 0, sys2: {"distance"}: 1}
        """
        # todo:change distance calculation to esi to enable detection out of the current map
        systems = {self: {"distance": 0}}
        current_distance = 0
        while current_distance < distance:
            current_distance += 1
            new_systems = []
            for system in systems.keys():
                for neighbour in system._neighbours:
                    if neighbour not in systems:
                        new_systems.append(neighbour)
            for newSystem in new_systems:
                systems[newSystem] = {"distance": current_distance}
        return systems

    def removeNeighbour(self, system):
        """
            Removes the link between to neighboured systems
        """
        if system in self._neighbours:
            self._neighbours.remove(system)
        if self in system._neighbours:
            system.neigbours.remove(self)

    def setStatus(self, new_status, alarm_time=datetime.datetime.utcnow()):
        if new_status == States.ALARM:
            self._last_alarm_timestamp = alarm_time.timestamp()
            if "stopwatch" not in self._second_line["class"]:
                self._second_line["class"].append("stopwatch")
            self.setBackgroundColor(self.ALARM_COLOR)
            self._first_line["style"] = self.SYSTEM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
            self._second_line["style"] = self.ALARM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
        elif new_status == States.CLEAR:
            self._last_alarm_timestamp = alarm_time.timestamp()
            self.setBackgroundColor(self.CLEAR_COLOR)
            if "stopwatch" not in self._second_line["class"]:
                self._second_line["class"].append("stopwatch")
            self._first_line["style"] = self.SYSTEM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
            self._second_line["style"] = self.ALARM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
        elif new_status == States.UNKNOWN:
            self.setBackgroundColor(self.UNKNOWN_COLOR)
            # second line in the rects is reserved for the clock
            self._second_line_flash = False
            self._first_line["style"] = self.SYSTEM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
            self._second_line["style"] = self.ALARM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
        if new_status not in (States.NOT_CHANGE, States.REQUEST):  # unknown not affect system status
            self.status = new_status

    def setStatistics(self, statistics):
        if self._svg_text is not None:
            if statistics is None:
                self._svg_text.string = "stats n/a"
            else:
                self._svg_text.string = "j-{jumps} f-{factionkills} s-{shipkills} p-{podkills}".format(**statistics)

    def update(self):
        last_cycle = True
        if self._currentStyle is not self.styles.currentStyle:
            self._currentStyle = self.styles.currentStyle
            self.updateStyle()

        alarm_time = datetime.datetime.utcnow().timestamp() - self._last_alarm_timestamp
        if self.status == States.ALARM:
            for maxDiff, alarmColour, lineColour in self.ALARM_COLORS:
                if alarm_time < maxDiff:
                    if self.backgroundColor != alarmColour:
                        self.backgroundColor = alarmColour
                        for rect in self._svg_element("rect"):
                            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                                rect["style"] = self.SYSTEM_STYLE.format(self.backgroundColor)
                        self.updateLineColour()
                    last_cycle = False
                    break
        elif self.status == States.CLEAR:
            for maxDiff, clearColour, lineColour in self.CLEAR_COLORS:
                if alarm_time < maxDiff:
                    if self.backgroundColor != clearColour:
                        self.backgroundColor = clearColour
                        for rect in self._svg_element("rect"):
                            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                                rect["style"] = self.SYSTEM_STYLE.format(self.backgroundColor)
                        self.updateLineColour()
                    last_cycle = False
                    break

        if self.status in (States.ALARM, States.CLEAR):
            if last_cycle:
                self._second_line_flash = False
                self.status = States.UNKNOWN
                self.setBackgroundColor(self.UNKNOWN_COLOR)
                self.updateLineColour()

            minutes = int(math.floor(alarm_time / 60))
            seconds = int(alarm_time - minutes * 60)

            self._second_line_flash = not self._second_line_flash
            if self._second_line_flash:
                self._second_line.string = "{m:02d}:{s:02d}".format(m=minutes, s=seconds, ticker=self.ticker)
            else:
                self._second_line.string = "{ticker}".format(m=minutes, s=seconds, ticker=self.ticker)

        else:
            self._second_line.string = self.ticker

    def updateLineColour(self):
        line_colour = self.textInv.getTextColourFromBackground(self.backgroundColor)
        self._first_line["style"] = self.SYSTEM_STYLE.format(line_colour)
        self._second_line["style"] = self.ALARM_STYLE.format(line_colour)

    def updateStyle(self):
        for i in range(5):
            self.ALARM_COLORS[i] = (self.ALARM_COLORS[i][0], self.styles.getCommons()["alarm_colours"][i],
                                    self.textInv.getTextColourFromBackground(self.ALARM_COLORS[i][1]))
        self.ALARM_COLOR = self.ALARM_COLORS[0][1]
        self.UNKNOWN_COLOR = self.styles.getCommons()["unknown_colour"]
        self.CLEAR_COLOR = self.styles.getCommons()["clear_colour"]
        line_colour = self.textInv.getTextColourFromBackground(self.backgroundColor)
        self._first_line["style"] = self.SYSTEM_STYLE.format(line_colour)
        self._second_line["style"] = self.ALARM_STYLE.format(line_colour)

        self.setBackgroundColor(self.UNKNOWN_COLOR)
        self.status = States.UNKNOWN

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
                    if solar_system_id == self.systemId:
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
            systemstats=self._svg_text.string,
            timers="",
            zkillinfo=""
        )

        for msg in self.messages:
            res = res + "<br/>" + msg.guiText
        return res

    def clearIntel(self):
        self.messages.clear()
        self.setStatus(States.UNKNOWN)

    def pruneMessage(self, message):
        if message in self.messages:
            self.messages.remove(message)

    def updateSVGText(self, soup) -> str:
        coordinates = self._map_coordinates
        text = "stats n/a"
        style = "text-anchor:middle;font-size:7;font-weight:normal;font-family:Arial;"
        self._svg_text = soup.new_tag("text", x=coordinates["center_x"], y=coordinates["y"] + coordinates["height"] + 2,
                                      fill="blue", style=style, visibility="hidden", transform=self._transform)
        self._svg_text["id"] = "stats_" + str(self.systemId)
        self._svg_text["class"] = "statistics"
        self._svg_text.string = text
        return self._svg_text
