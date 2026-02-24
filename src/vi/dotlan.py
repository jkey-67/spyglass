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


from vi.system import ALL_SYSTEMS, Universe


JB_COLORS = ("66CD00", "7CFC00", "7CFC00", "00FF00", "ADFF2F", "9ACD32", "00FA9A"
             "90EE90", "8FBC8F", "20B2AA", "2E8B57", "808000", "6B8E23")


class Map:
    """
        The map transfers the system related information from a dotlan svg to
        the internal System representation and setups a cache for the given region.
    """

    @staticmethod
    def setIncursionSystems(incursions:dict):
        """
        Mark all incursion systems on the current map
        Args:
            incursions(list(int)): list of system ids

        Returns:
            None

        """
        for incursion in incursions:
            lst_system_ids = incursion.get("infested_solar_systems")
            if lst_system_ids is None:
                continue
            staging_solar_system_id = incursion.get("staging_solar_system_id")
            if staging_solar_system_id is None:
                continue
            has_boss = incursion.get("has_boss",False)
            for sys_id in lst_system_ids:
                sys = ALL_SYSTEMS.get(sys_id)
                if sys is None:
                    continue
                sys.setIncursion(has_incursion=sys_id in lst_system_ids,
                                 is_staging=sys_id == staging_solar_system_id,
                                 has_boss=has_boss,
                                 influence=incursion.get("influence",0.0),
                                 state=incursion.get("state",""))

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

    @staticmethod
    def is_dirty():
        """
            Checks all systems for repaint
        Returns:
            True if at least one system on the map needs to be repainted or if the map is empty
        """
        return  any(sys.is_dirty for sys in ALL_SYSTEMS.values())

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

    @staticmethod
    def updateStyle():
        for system in ALL_SYSTEMS.values():
            system.updateStyle()

