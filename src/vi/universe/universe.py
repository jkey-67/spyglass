###########################################################################
#  EVE-Spyglass - Visual Intel Chat Analyzer                              #
#  Copyright (C) 2022 Nele McCool (nele.mccool @ gmx.net)                 #
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

import json
import os
from .shipnames import SHIPNAMES
from .npcnames import NPCNAMES

try:
    from .regionnames import REGION_IDS_BY_NAME
except (Exception,):
    REGION_IDS_BY_NAME = {}
    pass

try:
    from .constellationnames import CONSTELLATION_IDS_BY_NAME
except (Exception,):
    CONSTELLATION_IDS_BY_NAME = {}
    pass


def _loadJsonFile(name, **kw):
    with open(name, **kw) as fp:
        res = json.load(fp)
    return res


class Region(object):
    def __init__(self, **kwargs):
        self.constellations = list()
        self.description = str()
        self.name = str()
        self.region_id = int()
        self.__dict__.update(**kwargs)


class Position(object):
    def __init__(self, **kwargs):
        self.x = float()
        self.y = float()
        self.z = float()
        self.__dict__.update(**kwargs)


class Constellation(object):
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)
        self.region_id = int()
        self.systems = list()
        self.name = kwargs["name"]
        self.constellation_id = kwargs["constellation_id"]
        self.position = Position(**{"position": kwargs["position"]})


class Universe(object):
    curr_path = os.path.dirname(__file__)
    SYSTEMS = dict()
    SYSTEM_NAMES = list()
    UPPER_SYSTEM_NAMES = list()
    SYSTEM_IDS_BY_NAME = dict()
    SYSTEM_IDS_BY_UPPER_NAME = dict()
    try:
        SYSTEM_IDS_BY_NAME = _loadJsonFile(os.path.join(curr_path, "systemnames.json"), encoding="utf-8")
        for key, data in SYSTEM_IDS_BY_NAME.items():
            SYSTEM_IDS_BY_UPPER_NAME[key.upper()] = data

    except (Exception,):
        SYSTEM_IDS_BY_NAME = {}
        pass
    REGIONS = _loadJsonFile(os.path.join(curr_path, "everegions.json"))
    REGION_ID_OBJ = {region["region_id"]: Region(**region) for region in REGIONS}
    CONSTELLATIONS = _loadJsonFile(os.path.join(curr_path, "eveconstellations.json"))
    CONSTELLATIONS_ID_OBJS = {constellation["constellation_id"]: Constellation(**constellation) for constellation in CONSTELLATIONS}

    try:
        for system in _loadJsonFile(os.path.join(curr_path, "evesystems.json")):
            SYSTEMS[system["system_id"]] = system
            SYSTEM_NAMES.append(system["name"])
            UPPER_SYSTEM_NAMES.append(system["name"].upper())
    except (Exception,):
        pass

    STARGATES = _loadJsonFile(os.path.join(curr_path, "evestargates.json"))
    SHIP_NAMES = [sys["name"] for sys in SHIPNAMES]
    SHIP_NAMES.sort(key=lambda name: -len(name))
    NPC_FACTION_NAMES = NPCNAMES
    LOCATED_CHARS = set()

    def __init__(self):
        return

    @staticmethod
    def monitoredSystems(system_id, intel_range=3):
        mon_systems = {system_id:  {"dist": 0}} if system_id in Universe.SYSTEMS else None
        if mon_systems is not None:
            for distance in range(0, intel_range):
                for i in [{sys["destination"]["system_id"]: {"dist": distance + 1}} for sys in Universe.STARGATES if
                          sys["system_id"] in mon_systems.keys()]:
                    for key in list(i.keys()):
                        if key not in mon_systems.keys():
                            mon_systems.update(i)
        return mon_systems

    @staticmethod
    def npcFactionNames(faction_id: int, npc_list=None):
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
    def systemById(system_id):
        return Universe.SYSTEMS[system_id] if system_id in Universe.SYSTEMS else None

    @staticmethod
    def systemNameById(system_id):
        return Universe.SYSTEMS[system_id]["name"] if system_id in Universe.SYSTEMS else None

    @staticmethod
    def systemIdByName(system_name: str):
        system_id = Universe.SYSTEM_IDS_BY_NAME[system_name] if system_name in Universe.SYSTEM_IDS_BY_NAME else None
        if system_id is None and system_name in Universe.SYSTEM_IDS_BY_UPPER_NAME:
            system_id = Universe.SYSTEM_IDS_BY_UPPER_NAME[system_name]
        return system_id

    @staticmethod
    def regionIdByName(region_name: str):
        return REGION_IDS_BY_NAME[region_name] if region_name in REGION_IDS_BY_NAME else None

    @staticmethod
    def constellationIdByName(constellation_name: str):
        return CONSTELLATION_IDS_BY_NAME[constellation_name] \
            if constellation_name in CONSTELLATION_IDS_BY_NAME else None

    @staticmethod
    def shipNames():
        return Universe.SHIP_NAMES

    @staticmethod
    def regionByID(region_id):
        return next((rgn for rgn in Universe.REGIONS if rgn["region_id"] == region_id), None)

    @staticmethod
    def constellationByID(const_id):
        return next((const for const in Universe.CONSTELLATIONS if const["constellation_id"] == const_id), None)

    @staticmethod
    def stargatesBySystemID(system_id):
        res = list()
        for stargate in Universe.STARGATES:
            if stargate["system_id"] == system_id:
                res.append(stargate)
        return res

    @staticmethod
    def stargateByID(stargate_id):
        return next((stargate for stargate in Universe.STARGATES if stargate["stargate_id"] == stargate_id), None)

    @staticmethod
    def regionIDFromSystemID(system_id):
        if system_id in Universe.SYSTEMS:
            constellation_id = Universe.SYSTEMS[system_id]["constellation_id"]
            return next((sys["region_id"] for sys in Universe.CONSTELLATIONS \
                         if sys["constellation_id"] == constellation_id), None)
        else:
            return None

    @staticmethod
    def regionNameFromSystemID(system_id):
        region_id = Universe.regionIDFromSystemID(system_id)
        if region_id:
            region_name = next((sys["name"] for sys in Universe.REGIONS if sys["region_id"] == region_id), None)
            return region_name
        else:
            return None
