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

from PySide6.QtCore import QRectF, QSizeF, QPointF
from bs4 import BeautifulSoup
from vi.system import System, ALL_SYSTEMS, Universe


JB_COLORS = ("66CD00", "7CFC00", "7CFC00", "00FF00", "ADFF2F", "9ACD32", "00FA9A"
             "90EE90", "8FBC8F", "20B2AA", "2E8B57", "808000", "6B8E23")


def _extractPositionsFromSoup(soup) -> dict[int, (str, float, float)]:
    """
    Extracts all systems from the svg

    Remark:
        Depending on the current scaling the svg will be scanned for xlink:href tags #def... which wer interpreted as
        system idents, x and y attributes will be used as center for the system map.

    Args:
        soup(BeautifulSoup): BeautifulSoup holding the svg

    Returns:
        dict[int,(str,float,float)]:Dictionary hold all systems positions from the map

    """
    # default size of the systems to calculate the center point
    systems_map_new = dict()
    for use in soup.select("use"):
        if use.has_attr("xlink:href") and use.has_attr("x") and use.has_attr("y"):
            system_attr = use.attrs["xlink:href"]
            if system_attr.startswith("#def"):
                system_id = int(use.attrs["xlink:href"][4:])
                if system_id in ALL_SYSTEMS:
                    system = ALL_SYSTEMS[system_id]
                    systems_map_new[system_id] = (system.name, float(use.attrs["x"]), float(use.attrs["y"]))
    return systems_map_new


def _extractSizeFromSoup(soup, scale=1.0):
    """
    Setups width and height from the svg viewbox as x y w h
    Args:
        soup:

    Returns:
        None
    """
    svg = soup.select("svg")[0]
    box = svg["viewbox"] if "viewbox" in svg else None
    pos_x = []
    pos_y = []
    if box:
        box = box.split(" ")
        return QSizeF(float(box[2])*scale, float(box[3])*scale)
    else:
        return QSizeF(20*System.ELEMENT_WIDTH*scale, 20*System.ELEMENT_HEIGHT*scale)
        for system_id, data in _extractPositionsFromSoup(soup).items():
            pt = QRectF(
                data[1] * scale, data[2] * scale,
                System.ELEMENT_WIDTH, System.ELEMENT_HEIGHT).center()
            pos_x.append(float(pt.x()))
            pos_y.append(float(pt.y()))
        if len(pos_x):
            return QSizeF(max(pos_x)-min(pos_x)+System.ELEMENT_WIDTH, max(pos_y)-min(pos_y)+System.ELEMENT_HEIGHT)
        else:
            return QSizeF(System.ELEMENT_WIDTH, System.ELEMENT_HEIGHT)


def _extractSystemsFromSoup(soup, scale=1.0) -> dict[str, System]:
    """
    Extracts all systems from the svg

    Remark:
        Depending on the current scaling the svg will be scanned for system ids

    Args:
        soup(BeautifulSoup):
            BeautifulSoup holding the svg as html page
        scale(float):
            Scaling factor for the distance in between the systems base on 1027x768 DotLan SVG Maps, the default is 1.2

    Returns:
        dict[str,System]:Dictionary hold all systems from the map (str,System)

    """
    # default size of the systems to calculate the center point
    systems = {}
    for system_id, data in _extractPositionsFromSoup(soup).items():
        new_system = ALL_SYSTEMS[system_id]
        new_system.applySVG(
            map_coordinates=QRectF(
                data[1] * scale,
                data[2] * scale,
                System.ELEMENT_WIDTH,
                System.ELEMENT_HEIGHT))
        systems[new_system.name] = new_system
    return systems


class Map(object):
    """
        The map transfers the system related information from a dotlan svg to
        the internal System representation and setup a cache for the given region.
    """
    default_scale = 1.3

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
                 set_adm_visible=False,
                 set_jump_bridges=None):

        self.region_name = region_name
        self.region_id = Universe.regionIdByName(region_name)
        self._jumpMapsVisible = set_jump_maps_visible
        self._statisticsVisible = set_statistic_visible
        self._set_vulnerable_visible = set_adm_visible

        # Create soup from the svg
        svg_content = BeautifulSoup(svg_file, "lxml-xml")
        self.svg_size = _extractSizeFromSoup(svg_content, scale=self.default_scale)
        self.systems = _extractSystemsFromSoup(svg_content, scale=self.default_scale)

        self.systemsById = {}
        self.systemsByName = {}
        for system in self.systems.values():
            self.systemsById[system.system_id] = system
            self.systemsByName[system.name] = system

        self.jumpBridges = []
        self.marker = 0.0

        if set_jump_bridges:
            self.setJumpbridges(set_jump_bridges)

        self._updateJumpbridgesVisibility()
        self._updateVulnerableVisibility()
        self._updateStatisticsVisibility()

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

    @staticmethod
    def setSystemSovereignty(systems_stats):
        for system_id, sys_stats in systems_stats.items():
            if "ticker" in sys_stats:
                sys = ALL_SYSTEMS[int(system_id)]
                sys.ticker = sys_stats["ticker"]

    @staticmethod
    def setSystemStructures(system_structures):
        for sys_stats in system_structures:
            sys = ALL_SYSTEMS[int(sys_stats["solar_system_id"])]
            sys.setVulnerabilityInfo(sys_stats)

    def renderLegend(self, painter):
        System.renderLegend(painter, self.region_name)

    def renderMap(self, painter):
        for system in self.systems.values():
            system.updateSystemBackgroundColors()
            system.renderBackground(painter, self.region_id)

        for system in self.systems.values():
            system.renderConnections(painter, self.region_id, self.systems)
            system.renderJumpBridges(painter, self.region_id, self.systems)
            system.renderWormHoles(painter, self.region_id, self.systems)

        for system in self.systems.values():
            system.renderSystemTexts(painter, self.region_id)

    def is_dirty(self):
        """
            Checks all systems for repaint
        Returns:
            True if at least one system on the map needs to be repainted or if the map is empty
        """
        for system in self.systems.values():
            if system.is_dirty:
                return True
        return len(self.systems) == 0

    @staticmethod
    def addSystemStatistics(statistics):
        """
        Applies the statistic values to the systems
        Args:
            statistics:

        Returns:

        """
        if statistics is not None:
            for system_id, data in statistics.items():
                ALL_SYSTEMS[system_id].setStatistics(data)

    @staticmethod
    def setJumpbridges(jumpbridges_data):
        """
            Adding the jumpbridges to the map soup; format of data:
            tuples with at least 3 values (sys1, connection, sys2) connection is <->
        """

        for system in ALL_SYSTEMS.values():
            system.jumpBridges.clear()

        for bridge in jumpbridges_data:
            sys1 = ALL_SYSTEMS[Universe.systemIdByName(bridge[0])]
            sys2 = ALL_SYSTEMS[Universe.systemIdByName(bridge[2])]
            sys1.jumpBridges.add(sys2)
            sys2.jumpBridges.add(sys1)

    @staticmethod
    def setTheraConnections(thera_connections):
        for system in ALL_SYSTEMS.values():
            system.wormhole_info.clear()
            system.theraWormholes.clear()

        for connection in thera_connections:
            sys1 = ALL_SYSTEMS[connection["in_system_id"]]
            sys2 = ALL_SYSTEMS[connection["out_system_id"]]
            sys1.theraWormholes.add(sys2)
            sys1.wormhole_info.append(connection)
            sys2.wormhole_info.append(connection)

    def changeVulnerableVisibility(self, selected: bool) -> bool:
        self._set_vulnerable_visible = selected
        self._updateVulnerableVisibility()
        return self._set_vulnerable_visible

    def _updateVulnerableVisibility(self) -> None:
        for system in self.systems.values():
            system.is_vulnerable_visible = self._set_vulnerable_visible

    def changeStatisticsVisibility(self, selected: bool) -> bool:
        self._statisticsVisible = selected
        for system in self.systems.values():
            system.is_statistics_visible = self._statisticsVisible
        return self._statisticsVisible

    def _updateStatisticsVisibility(self) -> None:
        for system in self.systems.values():
            system.is_statistics_visible = self._statisticsVisible

    def _updateJumpbridgesVisibility(self):
        for system in self.systems.values():
            system.is_jumpbridges_visible = self._jumpMapsVisible

    def changeJumpbridgesVisibility(self, selected: bool) -> bool:
        self._jumpMapsVisible = selected
        self._updateJumpbridgesVisibility()
        return self._jumpMapsVisible

    def updateStyle(self):
        for system in self.systems.values():
            system.updateStyle()

