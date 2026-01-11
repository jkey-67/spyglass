###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool@gmx.net)                   #
#                                                                         #
#  This program is free software: you can redistribute it and/or modify   #
#  it under the terms of the GNU General Public License as published by   #
#  the Free Software Foundation, either version 3 of the License, or      #
#  (at your option) any later version.                                    #
#                                                                         #
#  This program is distributed in the hope that it will be useful,        #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the           #
#  GNU General Public License for more details.                           #
#                                                                         #
#                                                                         #
#  You should have received a copy of the GNU General Public License      #
#  along with this program. If not, see <https://www.gnu.org/licenses/>.  #
###########################################################################


from __future__ import print_function
import os
import sys
import jsonlines
from bs4 import BeautifulSoup
from vi import evegate
from vi.universe import Universe

CREATE_DOT_FILE = False
ROUND_POSITION = True
sys.path.append('../')


def checkArguments(args):
    error = False
    for path in args[1:3]:
        if not os.path.exists(path):
            errout("ERROR: {0} does not exist!".format(path))
            error = True
    if error:
        sys.exit(2)



def is_diffrent_region(src, dst):
    rgn_src = evegate.esiUniverseConstellations(src["constellation_id"], True)
    rgn_dst = evegate.esiUniverseConstellations(dst["constellation_id"], True)
    return rgn_src["region_id"] != rgn_dst["region_id"]


def is_different_constellation(src, dst):
    return src["constellation_id"] != dst["constellation_id"]

def systemsInSameConstellation(id_src, id_dst) -> bool:
    return Universe.systemById(id_src)["constellation_id"] == Universe.systemById(id_dst)["constellation_id"]

def systemsInSameRegion(id_src, id_dst) -> bool:

    return Universe.constellationByID(Universe.systemById(id_src)["constellation_id"]).region_id ==\
        Universe.constellationByID(Universe.systemById(id_dst)["constellation_id"]).region_id

def createJsonFile(region_ids:list[int]):
    """
        https://developers.eveonline.com/docs/guides/map-data/#2d-schematic-map
    Args:
        region_ids:
    Returns:

    """
    affected_systems = set()
    for region_id in region_ids:
        region_used = Universe.regionByID(region_id)
        for const_id in region_used.constellations:
            constellation_used = Universe.constellationByID(const_id)
            for system_id in constellation_used.systems:
                affected_systems.add(system_id)
                for stargate_system_0 in Universe.stargatesBySystemID(system_id):
                    affected_systems.add(stargate_system_0.destination.system_id)
                    for stargate_system_1 in Universe.stargatesBySystemID(stargate_system_0.destination.system_id):
                        affected_systems.add(stargate_system_1.destination.system_id)
                        continue
                        for stargate_system_2 in Universe.stargatesBySystemID(stargate_system_1.destination.system_id):
                            affected_systems.add(stargate_system_2.destination.system_id)
                            continue
                            for stargate_system_3 in Universe.stargatesBySystemID(stargate_system_2.destination.system_id):
                                affected_systems.add(stargate_system_3.destination.system_id)
                                for stargate_system_4 in Universe.stargatesBySystemID(stargate_system_3.destination.system_id):
                                    affected_systems.add(stargate_system_4.destination.system_id)
                                    continue

    graph_positions = dict()

    for system_id in affected_systems:
        system = Universe.systemById(system_id)
        name = system["name"]
        x_cur =  system["position"]["x"]*1e-14
        y_cur = -system["position"]["y"]*1e-14
        graph_positions[system_id] = (name, x_cur, y_cur)

    return graph_positions

def main():
    base_path = os.path.join(
        os.path.expanduser("~"), "projects", "spyglass", "src", "vi", "ui", "res", "mapdata" )

    new_eden = []
    jove = []
    for key, _ in Universe.REGIONS.items():
        if key <= 10_999_999:
            new_eden.append(key)
        else:
            jove.append(key)

    new_eden_regions = createJsonFile(new_eden)
    with jsonlines.open(
            "../vi/ui/res/mapdata/{}.jsonl".format("New_Eden"),
            mode='w') as writer:
        writer.write_all(new_eden_regions.items())

    jove_regions = createJsonFile(jove)
    with jsonlines.open(
            "../vi/ui/res/mapdata/{}.jsonl".format("Jove"),
            mode='w') as writer:
        writer.write_all(jove_regions.items())

    for key,region in Universe.REGIONS.items():
        region_name = region["name"]
        region_id = region["region_id"]
        new_svg = createJsonFile([region_id])
        with jsonlines.open("../vi/ui/res/mapdata/{}.jsonl".format(evegate.convertRegionNameForDotlan(region_name)), mode='w') as writer:
            writer.write_all(new_svg.items())

        with jsonlines.open("../vi/ui/res/mapdata/{}.jsonl".format(evegate.convertRegionNameForDotlan(region_name)), mode='r') as reader:
            new_svg_in = dict(reader)


def errout(*objs):
    print(*objs, file=sys.stderr)


if __name__ == "__main__":
    main()
