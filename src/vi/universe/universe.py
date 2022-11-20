import json
import os
from vi.universe.shipnames import SHIPNAMES
from vi.universe.npcnames import NPCNAMES


def _loadJsonFile(name):
    with open(name) as fp:
        res = json.load(fp)
    return res


class Universe(object):
    curr_path = os.path.dirname(__file__)
    STARGATES = _loadJsonFile(os.path.join(curr_path, "evestargates.json"))
    CONSTELLATIONS = _loadJsonFile(os.path.join(curr_path, "eveconstellations.json"))
    REGIONS = _loadJsonFile(os.path.join(curr_path, "everegions.json"))
    SYSTEMS = _loadJsonFile(os.path.join(curr_path, "evesystems.json"))
    SYSTEM_NAMES = [sys["name"] for sys in SYSTEMS]
    UPPER_SYSTEM_NAMES = [sys["name"].upper() for sys in SYSTEMS]
    SHIP_NAMES = [sys["name"] for sys in SHIPNAMES]
    NPC_FACTION_NAMES = NPCNAMES
    LOCATED_CHARS = set()

    def __init__(self, path_to_sql_file="cache.sqlite3"):
        return

    @staticmethod
    def monitoredSystems(system_id, intel_range=3):
        mon_systems = next(({sys["system_id"]: {"dist": 0}} for sys in Universe.SYSTEMS if sys["system_id"] == system_id), None)
        if mon_systems is not None:
            for distance in range(0, intel_range):
                for i in [{sys["destination"]["system_id"]: {"dist": distance + 1}} for sys in Universe.STARGATES if
                          sys["system_id"] in mon_systems.keys()]:
                    for key in list(i.keys()):
                        if key not in mon_systems.keys():
                            mon_systems.update(i)
        return mon_systems

    @staticmethod
    def npcFactionNames(faction_id: int, npc_list=list()):
        if faction_id in Universe.NPC_FACTION_NAMES:
            return Universe.NPC_FACTION_NAMES[faction_id]
        elif faction_id in npc_list:
            return npc_list[faction_id]
        else:
            return "???"


    @staticmethod
    def systemNames():
        return Universe.SYSTEM_NAMES

    @staticmethod
    def systemNamesUpperCase():
        return Universe.UPPER_SYSTEM_NAMES

    @staticmethod
    def systemNameById(system_id):
        return next((sys["name"] for sys in Universe.SYSTEMS if sys["system_id"] == system_id), None)

    @staticmethod
    def systemIdByName(system_name: str):
        return next((sys["system_id"] for sys in Universe.SYSTEMS if sys["name"].upper() == system_name.upper()), None)

    @staticmethod
    def shipNames():
        return Universe.SHIP_NAMES

    @staticmethod
    def regionIDFromSystemID(system_id):
        constellation_id = next((sys["constellation_id"] for sys in Universe.SYSTEMS if sys["system_id"] == system_id), None)
        return next((sys["region_id"] for sys in Universe.CONSTELLATIONS if sys["constellation_id"] == constellation_id), None)

    @staticmethod
    def regionNameFromSystemID(system_id):
        region_id = Universe.regionIDFromSystemID(system_id)
        region_name = next((sys["name"] for sys in Universe.REGIONS if sys["region_id"] == region_id), None)
        return region_name
