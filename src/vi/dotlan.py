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

import logging
from os import path
from bs4 import BeautifulSoup
from vi.ui.styles import Styles
from vi.system import System, ALL_SYSTEMS
from vi.universe import Universe

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
    def is_dirty(self):
        for system in self.systems.values():
            if system.is_dirty:
                return True
        return False

    @staticmethod
    def setIncursionSystems(incursions):
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
            for sys_id in lst_system_ids:
                sys = ALL_SYSTEMS[sys_id]
                sys.setIncursion(has_incursion=sys_id in lst_system_ids,
                                 is_staging=sys_id == staging_solar_system_id,
                                 has_boss=has_boss)

    def __init__(self,
                 region_name,
                 svg_file,
                 set_jump_maps_visible=False,
                 set_statistic_visible=False,
                 set_jump_bridges=None):

        self.region_name = region_name
        self.region_id = Universe.regionIdByName(region_name)
        self.width = 1024   # default size
        self.height = 768   # default size
        self.outdatedCacheError = None
        self._jumpMapsVisible = set_jump_maps_visible
        self._statisticsVisible = set_statistic_visible

        # Create soup from the svg
        self.soup = BeautifulSoup(svg_file, features="html.parser")
        self.systems = self._extractSystemsFromSoup(self.soup, 1.0)

        self.systemsById = {}
        self.systemsByName = {}
        for system in self.systems.values():
            self.systemsById[system.system_id] = system
            self.systemsByName[system.name] = system

        self._extractSizeFromSoup(self.soup)
        self.jumpBridges = []
        self.marker = 0.0

        if set_jump_bridges:
            self.setJumpbridges(set_jump_bridges)

    @staticmethod
    def setCampaignsSystems(lst_system_ids):
        """
        Marks all campaign systems on map
        Args:
            lst_system_ids(list(int)): list of system ids

        Returns:
            None
        """
        if lst_system_ids:
            for sys_id, sys in ALL_SYSTEMS.items():
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

    def _extractSystemsFromSoup(self, soup, scale=1.0) -> dict[str, System]:
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

                map_coordinates["center_x"] = (map_coordinates["x"] + 1.0+56.0/2.0)
                map_coordinates["center_y"] = (map_coordinates["y"] + (map_coordinates["height"] / 2.0))
                try:
                    if symbol_id in uses.keys():
                        system = ALL_SYSTEMS[system_id]
                        system.applySVG(
                            map_coordinates=map_coordinates)
                        systems[name] = system
                    else:
                        logging.error("System {} not found.".format(name))

                except KeyError:
                    logging.critical("Unable to prepare system {}.".format(name))
                    pass
        return systems

    @staticmethod
    def setSystemSovereignty(systems_stats):
        for system_id, sys_stats in systems_stats.items():
            if "ticker" in sys_stats:
                sys = ALL_SYSTEMS[int(system_id)]
                sys.ticker = sys_stats["ticker"]

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

    def render(self, painter):
        for system in self.systems.values():
            system.updateSVG()
            system.renderBackground(painter, self.region_id)

        for system in self.systems.values():
            system.renderConnections(painter, self.region_id, self.systems)
            system.renderJumpBridges(painter, self.region_id, self.systems)
            system.renderWormHoles(painter, self.region_id, self.systems)

        for system in self.systems.values():
            system.renderSystem(painter, self.region_id)

    @staticmethod
    def addSystemStatistics(statistics):
        """
        Appyes the statistic values to the systems
        Args:
            statistics:

        Returns:

        """
        if statistics is not None:
            for system_id, data in statistics.items():
                ALL_SYSTEMS[system_id].setStatistics(data)

    def setJumpbridges(self, jumpbridges_data):
        """
            Adding the jumpbridges to the map soup; format of data:
            tuples with at least 3 values (sys1, connection, sys2) connection is <->
        """

        for system in ALL_SYSTEMS.values():
            system.jumpBridges = set()

        for bridge in jumpbridges_data:
            sys1 = ALL_SYSTEMS[Universe.systemIdByName(bridge[0])]
            sys2 = ALL_SYSTEMS[Universe.systemIdByName(bridge[2])]
            sys1.jumpBridges.add(sys2)
            sys2.jumpBridges.add(sys1)

        self.updateJumpbridgesVisibility()

    def setTheraConnections(self, theraConnextions):
        for system in ALL_SYSTEMS.values():
            system.theraWormholes = set()

        for bridge in theraConnextions:
            sys1 = ALL_SYSTEMS[Universe.systemIdByName(bridge[0])]
            sys2 = ALL_SYSTEMS[Universe.systemIdByName(bridge[2])]
            sys1.jumpBridges.add(sys2)
            sys2.jumpBridges.add(sys1)

        self.updateJumpbridgesVisibility()

    def updateStatisticsVisibility(self):
        for system in self.systems.values():
            system.is_statistics_visible = self._statisticsVisible

    def changeStatisticsVisibility(self, selected: bool) -> bool:
        self._statisticsVisible = selected
        self.updateStatisticsVisibility()
        return self._statisticsVisible

    def updateJumpbridgesVisibility(self):
        for system in self.systems.values():
            system.is_jumpbridges_visible = self._jumpMapsVisible

    def changeJumpbridgesVisibility(self, selected: bool) -> bool:
        self._jumpMapsVisible = selected
        self.updateJumpbridgesVisibility()
        return self._jumpMapsVisible

    def debugWriteSoup(self):
        svg_data = self.soup.prettify("utf-8")
        for system in self.systems.values():
            if system.is_dirty:
                system.updateSVG()
        try:
            file_name = path.expanduser("~/projects/spyglass/src/vi/ui/res/mapdata_processed/{}.svg".format(self.region_name))
            with open(file_name, "wb") as svgFile:
                svgFile.write(svg_data)
                svgFile.close()
        except Exception as e:
            logging.error(e)
