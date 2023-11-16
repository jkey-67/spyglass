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
from requests import get as getRequest
from os import path
import datetime
import logging
import json
from bs4 import BeautifulSoup
from vi import states
from vi.cache.cache import Cache
from vi.ui.styles import Styles, TextInverter

JB_COLORS = ("66CD00", "7CFC00", "7CFC00", "00FF00", "ADFF2F", "9ACD32", "00FA9A"
             "90EE90", "8FBC8F", "20B2AA", "2E8B57", "808000", "6B8E23")


class DotlanException(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)


class Map(object):
    """
        The map including all information from dotlan
    """
    # todo : dark.svgs should follow stylesheet

    styles = Styles()

    @property
    def svg(self):
        # Re-render all systems
        for system in self.systems.values():
            system.update()

        # Update the marker, the marker should be visible for 20s
        if float(self.marker["opacity"]) > 0.0:
            delta = datetime.datetime.utcnow().timestamp() - float(self.marker["activated"])
            new_opacity = (1.0-delta/20.0)
            if new_opacity < 0:
                new_opacity = 0.0
            self.marker["opacity"] = str(new_opacity)

        return str(self.soup)

    def __init__(self, region,
                 svgFile=None,
                 setJumpMapsVisible=False,
                 setSatisticsVisible=False,
                 setSystemStatistic=None,
                 setJumpBridges=None,
                 setCampaignsSystems=None,
                 setIncursionSystems=None,
                 setPlayerSovereignty=None):
        self.region = region
        self.width = 1024   # default size
        self.height = 768   # default size
        cache = Cache()
        self.outdatedCacheError = None
        self._jumpMapsVisible = setJumpMapsVisible
        self._statisticsVisible = setSatisticsVisible
        if self.region == "Providencecatch" or self.region == "Providence-catch-compact":
            region_to_load = convertRegionName("providence-catch")
        else:
            region_to_load = convertRegionName(self.region)

        # Get map from dotlan if not in the cache
        # svg = cache.getFromCache("map_{}".format(region_to_load)) if svgFile is None else svgFile
        """
            if svg is None or svg.startswith("region not found"):
            try:
                svg = evegate.getSvgFromDotlan(region_to_load)
                if not svg or svg.startswith("region not found"):
                    region_to_load = "Providence"
                    svg = self._getSvgFromDotlan("providence")
                else:
                    cache.putIntoCache("map_{}".format(region_to_load), svg, 24 * 60 * 60)
            except Exception as e:
                self.outdatedCacheError = e
                svg = cache.getFromCache("map_{}".format(region_to_load))
                if not svg or svg.startswith("region not found"):
                    t = "No Map in cache, nothing from dotlan. Must give up " \
                        "because this happened:\n{0} {1}\n\nThis could be a " \
                        "temporary problem (like dotlan is not reachable), or " \
                        "everything went to hell. Sorry. This makes no sense " \
                        "without the map.\n\nRemember the site for possible " \
                        "updates: https://github.com/Crypta-Eve/spyglass".format(type(e), str(e))
                    raise DotlanException(t)
        """
        # Create soup from the svg
        self.soup = BeautifulSoup(svgFile, features="html.parser")
        for scr in self.soup.findAll('script'):
            scr.extract()
        for scr in self.soup.select('#controls'):
            scr.extract()

        for tag in self.soup.findAll(attrs={"onload": True}):
            del (tag["onload"])

        if "compact" in self.region:
            scale = 0.9
        elif "tactical" in self.region:
            scale = 1.5
        else:
            scale = 1.0

        self.systems = self._extractSystemsFromSoup(self.soup, scale)

        self.systemsById = {}
        for system in self.systems.values():
            self.systemsById[system.systemId] = system

        self.systemsByName = {}
        for system in self.systems.values():
            self.systemsByName[system.name] = system

        self._extractSizeFromSoup(self.soup)
        self._prepareSvg(self.soup)
        self._connectNeighbours()
        self.jumpBridges = cache.getJumpGates()
        self.marker = self.soup.select("#select_marker")[0]

        if setSystemStatistic:
            self.addSystemStatistics(setSystemStatistic)
        if setJumpBridges:
            self.setJumpbridges(setJumpBridges)
        if setCampaignsSystems:
            self.setCampaignsSystems(setCampaignsSystems)
        if setIncursionSystems:
            self.setIncursionSystems(setIncursionSystems)
        if setPlayerSovereignty:
            self.setSystemSovereignty(setPlayerSovereignty)

    def setIncursionSystems(self, incursions):
        """
        Mark all incursion systems on the current map
        Args:
            incursions(list(int)): list of system ids

        Returns:
            None

        """
        for incursion in incursions:
            lst_system_ids = incursion["infested_solar_systems"]
            staging_solar_system_id = incursion["staging_solar_system_id"]
            has_boss = incursion["has_boss"]
            for sys_id, sys in self.systemsById.items():
                if sys_id in lst_system_ids:
                    sys.setIncursion(hasIncursion=sys_id in lst_system_ids,
                                     isStaging=sys_id == staging_solar_system_id,
                                     hasBoss=has_boss)

    def setCampaignsSystems(self, lst_system_ids):
        """
        Marks all campaign systems on map
        Args:
            lst_system_ids(list(int)): list of system ids

        Returns:
            None
        """
        if lst_system_ids is not None:
            for sys_id, sys in self.systemsById.items():
                sys.setCampaigns(sys_id in lst_system_ids)

    def _extractSizeFromSoup(self, soup):
        """
        Setups width and height from the svg viewbox
        Args:
            soup:

        Returns:
            None
        """
        svg = soup.select("svg")[0]
        box = svg["viewbox"]
        if box:
            box = box.split(" ")
            self.width = float(box[2])
            self.height = float(box[3])

    def _extractSystemsFromSoup(self, soup, scale=1.0):
        """
        Extracts all systems from the svg

        Remark:
            Depending on the current scaling the svg will be modified

        Args:
            soup(BeautifulSoup): BeautifulSoup holding the svg
            scale(float): optional scaling factor

        Returns:
            dict[str,System]:Dictionary hold all systems from the map (str,System)

        """
        # default size of the systems to calculate the center point
        svg_width = 62.5
        svg_height = 30
        systems = {}
        uses = {}
        for use in soup.select("use"):
            use_id = use["xlink:href"][1:]
            use.attrs["width"] = str(svg_width)
            use.attrs["height"] = str(svg_height)
            use.attrs["x"] = str(float(use.attrs["x"]) * scale)
            use.attrs["y"] = str(float(use.attrs["y"]) * scale)
            uses[use_id] = use

        for use in soup.select("line"):
            use.attrs["x1"] = str((float(use.attrs["x1"])-svg_width/2.0) * scale+svg_width/2.0)
            use.attrs["y1"] = str((float(use.attrs["y1"])-svg_height/2.0) * scale+svg_height/2.0)
            use.attrs["x2"] = str((float(use.attrs["x2"])-svg_width/2.0) * scale+svg_width/2.0)
            use.attrs["y2"] = str((float(use.attrs["y2"])-svg_height/2.0) * scale+svg_height/2.0)

        symbols = soup.select("symbol")
        for symbol in symbols:
            symbol_id = symbol["id"]
            system_id = symbol_id[3:]
            try:
                system_id = int(system_id)
            except (ValueError,):
                continue
            for element in symbol.select(".sys"):
                name = element.select("text")[0].text.strip()
                map_coordinates = {}
                for keyname in ("x", "y", "width", "height"):
                    try:
                        map_coordinates[keyname] = float(uses[symbol_id][keyname])
                    except KeyError:
                        map_coordinates[keyname] = 0

                map_coordinates["center_x"] = (map_coordinates["x"] + 1.0+56.0/2.0)  # (mapCoordinates["width"] / 2.0))
                map_coordinates["center_y"] = (map_coordinates["y"] + (map_coordinates["height"] / 2.0))
                try:
                    if symbol_id in uses.keys():
                        if uses[symbol_id].find("transform"):
                            transform = uses[symbol_id]["transform"]
                        else:
                            transform = None
                        systems[name] = System(name, element, self.soup, map_coordinates, transform, system_id)
                    else:
                        logging.error("System {} not found.".format(name))

                except KeyError:
                    logging.critical("Unable to prepare system {}.".format(name))
                    pass

        return systems

    def setSystemSovereignty(self, systems_stats):
        for sys_id, sys in self.systemsById.items():
            sid = str(sys_id)
            if sid in systems_stats:
                if "ticker" in systems_stats[sid]:
                    sys.ticker = systems_stats[sid]["ticker"]

    @staticmethod
    def _prepareGradients(soup: BeautifulSoup):
        """
        Patch all radialGradient to the svg
        Args:
            soup(BeautifulSoup):BeautifulSoup holding the svg

        Returns:

        """
        use_radial_gradient = "radialGradient"
        grad_located = soup.new_tag(use_radial_gradient, id="grad_located", r="0.5")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#8b008d"
        stop["stop-opacity"] = "1.0"
        grad_located.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#8b008d"
        stop["stop-opacity"] = "0.0"
        grad_located.append(stop)

        grad_watch = soup.new_tag(use_radial_gradient, id="grad_watch", r="0.5")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#909090"
        stop["stop-opacity"] = "1.0"
        grad_watch.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#909090"
        stop["stop-opacity"] = "0.0"
        grad_watch.append(stop)

        grad_cam_bg = soup.new_tag(use_radial_gradient, id="camBg", r="0.5")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#FF8800"
        stop["stop-opacity"] = "1"
        grad_cam_bg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#FF8800"
        stop["stop-opacity"] = "0"
        grad_cam_bg.append(stop)

        grad_cam_active_bg = soup.new_tag(use_radial_gradient, id="camActiveBg", r="0.5")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#ff0000"
        stop["stop-opacity"] = "1.0"
        grad_cam_active_bg.append(stop)
        stop2 = soup.new_tag("stop")
        stop2["offset"] = "100%"
        stop2["stop-color"] = "#ff0000"
        stop2["stop-opacity"] = "0.0"
        grad_cam_active_bg.append(stop2)

        grad_inc_bg = soup.new_tag(use_radial_gradient, id="incBg", r="0.5")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#FFC800"
        stop["stop-opacity"] = "1"
        grad_inc_bg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#FFC800"
        stop["stop-opacity"] = "0"
        grad_inc_bg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#FFC800"
        stop["stop-opacity"] = "0"
        grad_inc_bg.append(stop)

        grad_inc_st_bg = soup.new_tag(use_radial_gradient, id="incStBg", r="0.5")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#FFC800"
        stop["stop-opacity"] = "1.0"
        grad_inc_st_bg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#FF0000"
        stop["stop-opacity"] = "0.0"
        grad_inc_st_bg.append(stop)

        grad_con_bg = soup.new_tag(use_radial_gradient, id="conBg", r="0.5")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#FFA0FF"
        grad_con_bg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "95%"
        stop["stop-color"] = "#FFA0FF"
        stop["stop-opacity"] = "0"
        grad_con_bg.append(stop)

        svg = soup.select("svg")[0]

        for grad in svg.findAll("radialGradient"):
            grad.extract()

        for grad in svg.findAll("radialgradient"):
            grad.extract()

        for defs in svg.select("defs"):
            defs.insert(0, grad_located)
            defs.insert(0, grad_watch)
            defs.insert(0, grad_cam_bg)
            defs.insert(0, grad_cam_active_bg)
            defs.insert(0, grad_inc_bg)
            defs.insert(0, grad_inc_st_bg)
            defs.insert(0, grad_con_bg)

    def _prepareSvg(self, soup):
        svg = soup.select("svg")[0]
        svg.attrs = {key: value for key, value in svg.attrs.items() if key not in ["style", "onmousedown", "viewbox"]}
        if self.styles.getCommons()["change_lines"]:
            for line in soup.select("line"):
                line["class"] = "j"

        # remove the box below the legend
        auto_rc = svg.find("rect", {"class", "lbt"})
        if auto_rc:
            auto_rc.decompose()

        # Current system marker ellipse
        group = soup.new_tag("g", id="select_marker", opacity="1.0", activated="0", transform="translate(0, 0)")
        ellipse = soup.new_tag("ellipse", cx="0", cy="0", rx="56", ry="28", style="fill:#462CFF")
        group.append(ellipse)

        self._prepareGradients(soup)

        # The giant cross-hairs
        for coord in ((0, -10000), (-10000, 0), (10000, 0), (0, 10000)):
            line = soup.new_tag("line", x1=coord[0], y1=coord[1], x2="0", y2="0", style="stroke:#462CFF")
            group.append(line)
        svg.insert(0, group)

        svg_map = svg.select("#map")

        for defs in svg.select("defs"):
            for tag in defs.select("a"):
                tag.attrs = {key: value for key, value in tag.attrs.items() if key not in ["target", "xlink:href"]}
                tag.name = "a"

        for defs in svg.select("defs"):
            for symbol in defs.select("symbol"):
                if symbol:
                    symbol.name = "g"
                    svg_map.insert(0, symbol)
        try:
            jumps = soup.select("#jumps")[0]
        except (Exception,):
            jumps = list()

        # Set up the tags for system statistics
        for systemId, system in self.systemsById.items():
            coords = system.mapCoordinates
            text = "stats n/a"
            style = "text-anchor:middle;font-size:7;font-weight:normal;font-family:Arial;"
            system.svgtext = soup.new_tag("text", x=coords["center_x"], y=coords["y"] + coords["height"] + 2,
                                          fill="blue", style=style, visibility="hidden", transform=system.transform)
            system.svgtext["id"] = "stats_" + str(systemId)
            system.svgtext["class"] = "statistics"
            system.svgtext.string = text
            jumps.append(system.svgtext)

    def _connectNeighbours(self):
        """
            This will find all neighbours of the systems and connect them.
            It takes a look at all the jumps on the map and gets the system under
            which the line ends

        Remark:
            Marking is based on the #jumps svg entries
        """
        for jump in self.soup.select("#jumps")[0].select(".j,.jc,.jr"):
            if "jumpbridge" in jump["class"]:
                continue
            parts = jump["id"].split("-")
            if parts[0] == "j":
                start_system = self.systemsById[int(parts[1])]
                stop_system = self.systemsById[int(parts[2])]
                start_system.addNeighbour(stop_system)


    def addSystemStatistics(self, statistics):
        """
        Appyes the statistic values to the systems
        Args:
            statistics:

        Returns:

        """
        if statistics is not None:
            for systemId, system in self.systemsById.items():
                if systemId in statistics.keys():
                    system.setStatistics(statistics[systemId])
        else:
            for system in self.systemsById.values():
                system.setStatistics(None)
        self.updateStatisticsVisibility()

    def setJumpbridges(self, jumpbridgesData):
        """
            Adding the jumpbridges to the map soup; format of data:
            tuples with at least 3 values (sys1, connection, sys2) connection is <->
        """
        # todo:disable jbs during init
        self.jumpBridges = []
        if jumpbridgesData is None:
            self.jumpBridges = []
            return
        soup = self.soup
        for bridge in soup.select(".jumpbridge"):
            bridge.decompose()

        for bridge in soup.select(".ansitext"):
            bridge.decompose()

        for ice_rect in soup.find_all("rect", {"class": "i"}):
            ice_rect.decompose()

        jumps = soup.select("#jumps")
        if jumps is not None:
            jumps = soup.select("#jumps")[0]
        else:
            return

        color_count = 0
        for bridge in jumpbridgesData:
            sys1 = bridge[0]
            connection = bridge[1]
            sys2 = bridge[2]
            one_systems_on_map = sys1 in self.systems or sys2 in self.systems
            both_systems_on_map = sys1 in self.systems and sys2 in self.systems

            if not one_systems_on_map:
                continue

            if color_count > len(JB_COLORS) - 1:
                color_count = 0
            jb_color = JB_COLORS[color_count]
            color_count += 1
            # Construct the line, color it and add it to the jumps
            if both_systems_on_map:
                system_one = self.systems[sys1]
                system_two = self.systems[sys2]
                self.jumpBridges.append([system_one.systemId, system_two.systemId])
                system_one_coords = system_one.mapCoordinates
                system_two_coords = system_two.mapCoordinates
                system_one_offset_point = system_one.getTransformOffsetPoint()
                system_two_offset_point = system_two.getTransformOffsetPoint()

                x1 = system_one_coords["center_x"] + system_one_offset_point[0]
                y1 = system_one_coords["center_y"] + system_one_offset_point[1]
                x2 = system_two_coords["center_x"] + system_two_offset_point[0]
                y2 = system_two_coords["center_y"] + system_two_offset_point[1]
                dx = (x2 - x1) / 2.0
                dy = (y2 - y1) / 2.0
                offset = 0.4 * math.sqrt(dx*dx+dy*dy)
                angle = math.atan2(dy, dx) - math.pi / 2.0
                mx = x1 + dx + offset * math.cos(angle)
                my = y1 + dy + offset * math.sin(angle)

                line = soup.new_tag("path", d="M{} {} Q {} {} {} {}".format(x1, y1, mx, my, x2, y2),
                                    visibility="hidden", fill="none", style="stroke:#{0}".format(jb_color))
                line["stroke-width"] = str(2)
                line["opacity"] = "0.8"
            else:
                source_system = self.systems[sys1] if sys1 in self.systems else self.systems[sys2] if sys2 in self.systems else None
                destination_name = sys2 if sys1 in self.systems else sys1
                if source_system is None:
                    continue
                system_one_coords = source_system.mapCoordinates
                system_two_coords = source_system.mapCoordinates

                system_one_offset_point = source_system.getTransformOffsetPoint()
                system_two_offset_point = source_system.getTransformOffsetPoint()

                x1 = system_one_coords["center_x"] + system_one_offset_point[0]
                y1 = system_one_coords["center_y"] + system_one_offset_point[1]
                x2 = system_two_coords["center_x"] + system_two_offset_point[0] + 30
                y2 = system_two_coords["center_y"] + system_two_offset_point[1] - 15
                dx = (x2 - x1) / 2.0
                dy = (y2 - y1) / 2.0
                offset = 0.4 * math.sqrt(dx*dx+dy*dy)
                angle = math.atan2(dy, dx) - math.pi / 2.0
                mx = x1 + dx + offset * math.cos(angle)
                my = y1 + dy + offset * math.sin(angle)
                # jbColor = "80c080"
                line = soup.new_tag("path", d="M{} {} Q {} {} {} {}".format(x1, y1, mx, my, x2, y2),
                                    visibility="hidden", fill="none", text="", style="stroke:#{0}".format(jb_color))
                line["stroke-width"] = "1"
                line["opacity"] = "0.8"

                text = soup.new_tag("text")
                text["class"] = "ansitext"
                text["x"] = "{}".format(0)
                text["y"] = "{}".format(0)
                text["fill"] = "#{0}".format(jb_color)
                text.string = destination_name
                text["text-anchor"] = "middle"
                text["alignment-baseline"] = "ideographic"
                text["fill-opacity"] = "0.8"
                text["font-size"] = "6px"
                text["transform"] = "translate({},{}) rotate(40)".format(x2, y2)
                jumps.append(text)

            line["class"] = "jumpbridge"

            jumps.insert(0, line)
        self.updateJumpbridgesVisibility()

    def updateStatisticsVisibility(self):
        value = "visible" if self._statisticsVisible else "hidden"
        for line in self.soup.select(".statistics"):
            line["visibility"] = value
            line["fill"] = "red"

    def changeStatisticsVisibility(self, selected: bool) -> bool:
        self._statisticsVisible = selected
        self.updateStatisticsVisibility()
        return self._statisticsVisible

    def updateJumpbridgesVisibility(self):
        value = "visible" if self._jumpMapsVisible else "hidden"
        for line in self.soup.select(".jumpbridge"):
            line["visibility"] = value
        for text in self.soup.select(".ansitext"):
            text["visibility"] = value

    def changeJumpbridgesVisibility(self, selected: bool) -> bool:
        self._jumpMapsVisible = selected
        self.updateJumpbridgesVisibility()
        return self._jumpMapsVisible

    def debugWriteSoup(self):
        svg_data = self.soup.prettify("utf-8")
        try:
            file_name = path.expanduser("~/projects/spyglass/src/{}.svg".format(self.region))
            with open(file_name, "wb") as svgFile:
                svgFile.write(svg_data)
                svgFile.close()
        except Exception as e:
            logging.error(e)


class System(object):
    """
        A System on the Map
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

    def __init__(self, name, svgElement, mapSoup, mapCoordinates, transform, systemId, ticker="npc"):
        self.status = states.UNKNOWN
        self.name = name
        self.ticker = ticker
        self.svgElement = svgElement
        self.mapSoup = mapSoup
        self.origSvgElement = svgElement
        self.rect = svgElement.select("rect")[0]
        self.firstLine = svgElement.select("text")[0]
        self.secondLine = svgElement.select("text")[1]
        self.secondLineFlash = False
        self.lastAlarmTimestamp = 0
        self.messages = []
        self.setStatus(states.UNKNOWN)
        self.__locatedCharacters = []
        self.backgroundColor = self.styles.getCommons()["bg_colour"]
        self.mapCoordinates = mapCoordinates
        self.systemId = systemId
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

    def getTransformOffsetPoint(self):
        if not self.cachedOffsetPoint:
            if self.transform:
                # Convert data in the form 'transform(0,0)' to a list of two floats
                point_string = self.transform[9:].strip('()').split(',')
                self.cachedOffsetPoint = [float(point_string[0]), float(point_string[1])]
            else:
                self.cachedOffsetPoint = [0.0, 0.0]
        return self.cachedOffsetPoint

    def mark(self):
        marker = self.mapSoup.select("#select_marker")[0]
        offset_point = self.getTransformOffsetPoint()
        x = self.mapCoordinates["center_x"] + offset_point[0]
        y = self.mapCoordinates["center_y"] + offset_point[1]
        marker["transform"] = "translate({x},{y})".format(x=x, y=y)
        marker["opacity"] = "1.0"
        marker["activated"] = datetime.datetime.utcnow().timestamp()

    def addLocatedCharacter(self, char_name):
        id_name = self.name + u"_loc"
        was_located = bool(self.__locatedCharacters)
        if char_name not in self.__locatedCharacters:
            self.__locatedCharacters.append(char_name)
        if not was_located:
            coordinates = self.mapCoordinates
            new_tag = self.mapSoup.new_tag(
                "rect", x=coordinates["x"]-10, y=coordinates["y"]-8,
                width=coordinates["width"]+16, height=coordinates["height"]+16, id=id_name,
                rx=12, ry=12, fill="url(#grad_located)")
            jumps = self.mapSoup.select("#jumps")[0]
            jumps.insert(0, new_tag)

    def setCampaigns(self, campaigns: bool):
        id_name = self.name + u"_campaigns"
        if campaigns and not self.__hasCampaigns:
            camp_node = self.mapSoup.find(id=id_name)
            if camp_node is None:
                coordinates = self.mapCoordinates
                new_tag = self.mapSoup.new_tag(
                    "rect", x=coordinates["x"]-10, y=coordinates["y"]-8,
                    width=coordinates["width"]+16, height=coordinates["height"]+16, id=id_name,
                    rx=12, ry=12, fill="url(#camActiveBg)")
                jumps = self.mapSoup.select("#jumps")[0]
                jumps.insert(0, new_tag)
        elif not campaigns and self.__hasCampaigns:
            camp_node = self.mapSoup.find(id=id_name)
            camp_node.decompose()
        self.__hasCampaigns = campaigns

    def setIncursion(self, hasIncursion: bool = False, isStaging: bool = False, hasBoss: bool = False):
        id_name = self.name + u"_incursion"
        if hasIncursion and not self.__hasIncursion:
            curr_node = self.mapSoup.find(id=id_name)
            if curr_node is None:
                coords = self.mapCoordinates
                new_tag = self.mapSoup.new_tag("rect", x=coords["x"]-10, y=coords["y"]-8, width=coords["width"]+16,
                                               height=coords["height"]+16, id=id_name, rx=12, ry=12,
                                               fill="url(#incStBg)" if hasBoss else "url(#incBg)")
                jumps = self.mapSoup.select("#jumps")[0]
                jumps.insert(0, new_tag)
        elif not hasIncursion and self.__hasIncursion:
            camp_node = self.mapSoup.find(id=id_name)
            camp_node.decompose()
        self.__hasIncursion = hasIncursion
        self.__isStaging = isStaging
        self.__hasIncursionBoss = hasBoss

    def setBackgroundColor(self, color):
        for rect in self.svgElement("rect"):
            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                rect["style"] = "fill: {0};".format(color)
        self.backgroundColor = color

    def getLocatedCharacters(self):
        characters = []
        for char in self.__locatedCharacters:
            characters.append(char)
        return characters

    def removeLocatedCharacter(self, charname):
        id_name = self.name + u"_loc"
        if charname in self.__locatedCharacters:
            self.__locatedCharacters.remove(charname)
            if not self.__locatedCharacters:
                try:
                    elem = self.mapSoup.find(id=id_name)
                    if elem is not None:
                        logging.debug("removeLocatedCharacter {0} Decompose {1}".format(charname, str(elem)))
                        elem.decompose()
                except Exception as e:
                    logging.critical("Error in removeLocatedCharacter  {0}".format(str(e)))
                    pass

    def addNeighbour(self, neighbourSystem):
        """
            Add a neighbour system to this system
            neighbour_system: a system (not a system's name!)
        Args:
            neighbourSystem(System):
        """
        self.neighbours.add(neighbourSystem)
        neighbourSystem.neighbours.add(self)

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
                for neighbour in system.neighbours:
                    if neighbour not in systems:
                        new_systems.append(neighbour)
            for newSystem in new_systems:
                systems[newSystem] = {"distance": current_distance}
        return systems

    def removeNeighbour(self, system):
        """
            Removes the link between to neighboured systems
        """
        if system in self.neighbours:
            self.neighbours.remove(system)
        if self in system.neighbours:
            system.neigbours.remove(self)

    def setStatus(self, newStatus, alarm_time=datetime.datetime.utcnow()):
        if newStatus == states.ALARM:
            self.lastAlarmTimestamp = alarm_time.timestamp()
            if "stopwatch" not in self.secondLine["class"]:
                self.secondLine["class"].append("stopwatch")
            self.setBackgroundColor(self.ALARM_COLOR)
            self.firstLine["style"] = self.SYSTEM_STYLE.format(self.textInv.getTextColourFromBackground(self.backgroundColor))
            self.secondLine["style"] = self.ALARM_STYLE.format(self.textInv.getTextColourFromBackground(self.backgroundColor))
        elif newStatus == states.CLEAR:
            self.lastAlarmTimestamp = alarm_time.timestamp()
            self.setBackgroundColor(self.CLEAR_COLOR)
            if "stopwatch" not in self.secondLine["class"]:
                self.secondLine["class"].append("stopwatch")
            self.firstLine["style"] = self.SYSTEM_STYLE.format(self.textInv.getTextColourFromBackground(self.backgroundColor))
            self.secondLine["style"] = self.ALARM_STYLE.format(self.textInv.getTextColourFromBackground(self.backgroundColor))
        elif newStatus == states.UNKNOWN:
            self.setBackgroundColor(self.UNKNOWN_COLOR)
            # second line in the rects is reserved for the clock
            self.secondLineFlash = False
            self.firstLine["style"] = self.SYSTEM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
            self.secondLine["style"] = self.ALARM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
        if newStatus not in (states.NOT_CHANGE, states.REQUEST):  # unknown not affect system status
            self.status = newStatus

    def setStatistics(self, statistics):
        if self.svgtext is not None:
            if statistics is None:
                self.svgtext.string = "stats n/a"
            else:
                self.svgtext.string = "j-{jumps} f-{factionkills} s-{shipkills} p-{podkills}".format(**statistics)

    def update(self):
        last_cycle = True
        if self.currentStyle is not self.styles.currentStyle:
            self.currentStyle = self.styles.currentStyle
            self.updateStyle()

        alarm_time = datetime.datetime.utcnow().timestamp() - self.lastAlarmTimestamp
        if self.status == states.ALARM:
            for maxDiff, alarmColour, lineColour in self.ALARM_COLORS:
                if alarm_time < maxDiff:
                    if self.backgroundColor != alarmColour:
                        self.backgroundColor = alarmColour
                        for rect in self.svgElement("rect"):
                            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                                rect["style"] = self.SYSTEM_STYLE.format(self.backgroundColor)
                        self.updateLineColour()
                    last_cycle = False
                    break
        elif self.status == states.CLEAR:
            for maxDiff, clearColour, lineColour in self.CLEAR_COLORS:
                if alarm_time < maxDiff:
                    if self.backgroundColor != clearColour:
                        self.backgroundColor = clearColour
                        for rect in self.svgElement("rect"):
                            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                                rect["style"] = self.SYSTEM_STYLE.format(self.backgroundColor)
                        self.updateLineColour()
                    last_cycle = False
                    break

        if self.status in (states.ALARM, states.CLEAR):
            if last_cycle:
                self.secondLineFlash = False
                self.status = states.UNKNOWN
                self.setBackgroundColor(self.UNKNOWN_COLOR)
                self.updateLineColour()

            minutes = int(math.floor(alarm_time / 60))
            seconds = int(alarm_time - minutes * 60)

            if self.secondLineFlash:
                self.secondLine.string = "{m:02d}:{s:02d}".format(m=minutes, s=seconds, ticker=self.ticker)
            else:
                self.secondLine.string = "{ticker}".format(m=minutes, s=seconds, ticker=self.ticker)
            self.secondLineFlash = not self.secondLineFlash
        else:
            self.secondLine.string = self.ticker

    def updateLineColour(self):
        lineColour = self.textInv.getTextColourFromBackground(self.backgroundColor)
        self.firstLine["style"] = self.SYSTEM_STYLE.format(lineColour)
        self.secondLine["style"] = self.ALARM_STYLE.format(lineColour)

    def updateStyle(self):
        for i in range(5):
            self.ALARM_COLORS[i] = (self.ALARM_COLORS[i][0], self.styles.getCommons()["alarm_colours"][i],
                                    self.textInv.getTextColourFromBackground(self.ALARM_COLORS[i][1]))
        self.ALARM_COLOR = self.ALARM_COLORS[0][1]
        self.UNKNOWN_COLOR = self.styles.getCommons()["unknown_colour"]
        self.CLEAR_COLOR = self.styles.getCommons()["clear_colour"]
        self.setBackgroundColor(self.UNKNOWN_COLOR)
        self.status = states.UNKNOWN
        line_colour = self.textInv.getTextColourFromBackground(self.backgroundColor)
        self.firstLine["style"] = self.SYSTEM_STYLE.format(line_colour)
        self.secondLine["style"] = self.ALARM_STYLE.format(line_colour)

    def getTooltipText(self):
        format_src = '''<span style=" font-weight:600; color:#e5a50a;">{system}</span>'''\
                     '''<span style=" font-weight:600; font-style:italic; color:#deddda;">&lt;{ticker}&gt;</span>'''\
                     '''<br/><span style=" font-weight:600; color:#e01b24;">{systemstats}</span>'''

                     # '''<p><span style=" font-weight:600; color:#deddda;">{timers}</span></p>'''\
                     # '''<p><span style=" font-weight:600; color:#deddda;">{zkillinfo}</span></p>'''\

        if self.__hasIncursion:
            if self.__isStaging:
                format_src = format_src + '''<br/><span style=" font-weight:600; color:#ffcc00;">-Incursion Staging{}-</span>'''.format(" Boss" if self.__hasIncursionBoss else "")
            else:
                format_src = format_src + '''<br/><span style=" font-weight:600; color:#ff9900;">-Incursion{}-</span>'''.format(" Boss" if self.__hasIncursionBoss else "")

        if self.__hasCampaigns:
            cache_key = "sovereignty_campaigns"
            response = Cache().getFromCache(cache_key)
            if response:
                campaign_data = json.loads(response)
                for itm in campaign_data:
                    start_time = itm["start_time"]
                    solar_system_id = itm["solar_system_id"]
                    structure_id = itm["structure_id"]

                    cache_key = "_".join(("structure", "id", str(structure_id)))
                    cache = Cache()
                    cached_id = cache.getFromCache(cache_key, True)

                    event_type = itm["event_type"]
                    if solar_system_id == self.systemId:
                        if event_type == "tcu_defense":
                            format_src = format_src + '''<br/><span style=" font-weight:600; color:#c00000;">TCU {}</span>'''.format(start_time)
                        if event_type == "ihub_defense":
                            format_src = format_src + '''<br/><span style=" font-weight:600; color:#c00000;">IHUB {}</span>'''.format(start_time)
                        if event_type == "station_defense":
                            format_src = format_src + '''<br/><span style=" font-weight:600; color:#c00000;">Defense Events {}</span>'''.format(start_time)
                        if event_type == "station_freeport":
                            format_src = format_src + '''<br/><span style=" font-weight:600; color:#c00000;">Freeport Events {}</span>'''.format(start_time)

        res = format_src.format(
            system=self.name,
            ticker=self.ticker,
            systemstats=self.svgtext.string,
            timers="",
            zkillinfo=""
        )

        for msg in self.messages:
            res = res + "<br/>" + msg.guiText
        return res

    def clearIntel(self):
        self.messages.clear()
        self.setStatus( states.UNKNOWN )

    def pruneMessage(self, message):
        if message in self.messages:
            self.messages.remove(message)


# this is for testing:
if __name__ == "__main__":
    svg_map = Map("providence")
    s = map.systems["I7S-1S"]
    s.setStatus(states.ALARM)
    logging.error(map.svg)

