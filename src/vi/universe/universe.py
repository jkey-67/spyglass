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

import os
import json
import jsonlines
from typing import Optional
from .shipnames import ID_BY_SHIPNAMES
from .npcnames import NPCNAMES

try:
    from .regionnames import REGION_IDS_BY_NAME, REGION_NAME_BY_ID
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


class Position(object):
    USE_3D = False
    GL_MAP_FACTOR_2D = 1e-17*3.0
    GL_MAP_FACTOR_3D = 1e-18*4.0
    def __init__(self, **kwargs):
        self.x = float()
        self.y = float()
        self.z = float()
        self.__dict__.update(**kwargs)


class Region(object):
    def __init__(self, **kwargs):
        self.constellations = kwargs["constellations"]
        self.name = kwargs["name"]
        self.names = kwargs["names"]
        self.region_id = kwargs["region_id"]
        self.position2D = Position(** kwargs["position2D"])
        self.position3D = Position(** kwargs["position"])


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

class Constellation(object):
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)
        self.region_id = int()
        self.systems = kwargs["systems"]
        self.names = kwargs["names"]
        self.name = kwargs["name"]
        self.constellation_id = kwargs["constellation_id"]
        self.position2D = Position(** kwargs["position2D"])
        self.position3D = Position(** kwargs["position"])

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


class Destination(object):
    def __init__(self, **kwargs):
        self.system_id = kwargs["system_id"]
        self.stargate_id = kwargs["stargate_id"]

class Stargate(object):
    def __init__(self,stargate_id:int, **kwargs):
        self.__dict__.update(**kwargs)
        self.stargate_id = stargate_id
        self.system_id = kwargs["system_id"]
        self.destination = Destination(**kwargs["destination"])
        self.position2D = None # ALL_SYSTEMS.get(self.system_id).position2D
        self.position3D = Position(**kwargs["position"])

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


class Universe(object):
    curr_path = os.path.dirname(__file__)
    SYSTEMS = dict()
    STARGATES = dict()
    STARGATES_ID_OBJ:dict[int,Stargate] = dict()
    SYSTEM_NAMES:list[str] = list()
    UPPER_SYSTEM_NAMES:list[str] = list()
    SYSTEM_IDS_BY_NAME:dict[str,int] = dict()
    SYSTEM_IDS_BY_UPPER_NAME:dict[str,int] = dict()
    REGIONS:dict[int, dict] = dict()
    REGIONS_ID_OBJ:dict[int, Region] = dict()
    CONSTELLATIONS:dict[int, dict] = dict()
    CONSTELLATIONS_ID_OBJS:dict[int, Constellation]=dict()

    try:
        with jsonlines.open(os.path.join(curr_path, "systemnames.jsonl"), mode='r') as reader:
            for name,id in reader:
                SYSTEM_IDS_BY_NAME[name] = id
                SYSTEM_IDS_BY_UPPER_NAME[name.upper()] = id

    except (Exception,):
        SYSTEM_IDS_BY_NAME = dict()
        SYSTEM_IDS_BY_UPPER_NAME = dict()

    try:
        with jsonlines.open(os.path.join(curr_path, "everegions.jsonl"), mode='r') as reader:
            REGIONS = dict(reader)
        REGIONS_ID_OBJ = {key: Region(**region) for key,region in REGIONS.items()}
    except (Exception,):
        REGIONS = dict()
        REGIONS_ID_OBJ = dict()

    try:
        with jsonlines.open(os.path.join(curr_path, "eveconstellations.jsonl"), mode='r') as reader:
            CONSTELLATIONS = dict(reader)
        CONSTELLATIONS_ID_OBJS = {key: Constellation(**constellation) for key,constellation in CONSTELLATIONS.items()}
    except (Exception,):
        CONSTELLATIONS = dict()
        CONSTELLATIONS_ID_OBJS = dict()

    try:
        with jsonlines.open(os.path.join(curr_path, "evesystems.jsonl"), mode='r') as reader:
            for key,system in reader:
                SYSTEMS[key] = system
                SYSTEM_NAMES.append(system["name"])
                UPPER_SYSTEM_NAMES.append(system["name"].upper())
    except (Exception,):
        SYSTEMS = dict()
        SYSTEM_NAMES = list()
        UPPER_SYSTEM_NAMES = list()
    try:
        with jsonlines.open(os.path.join(curr_path, "evestargates.jsonl"), mode='r') as reader:
            for key,stargate in reader:
                STARGATES[key] = stargate
                STARGATES_ID_OBJ[key] = Stargate(key,**stargate)
    except (Exception,):
        STARGATES = dict()
        STARGATES_ID_OBJ = dict()

    # SHIP_NAMES = [sys["name"] for sys in SHIPNAMES]
    SHIP_NAMES = list(ID_BY_SHIPNAMES.keys())
    SHIP_NAMES.sort(key=lambda name: -len(name))
    NPC_FACTION_NAMES = NPCNAMES
    LOCATED_CHARS = set()

    def __init__(self):
        return

    @staticmethod
    def monitoredSystems(system_id:int, intel_range=3):
        mon_systems = {system_id:  {"dist": 0}} if system_id in Universe.SYSTEMS.keys() else None
        if mon_systems is not None:
            for distance in range(0, intel_range):
                for i in [{stargate.destination.system_id: {"dist": distance + 1}} for stargate in Universe.STARGATES_ID_OBJ.values() if stargate.system_id in mon_systems.keys()]:
                    for key in i.keys():
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
    def systemNameById(system_id:int)->Optional[dict]:
        return Universe.SYSTEMS[system_id]["name"] if system_id in Universe.SYSTEMS else None

    @staticmethod
    def systemIdByName(system_name: str)->Optional[int]:
        system_id = Universe.SYSTEM_IDS_BY_NAME[system_name] if system_name in Universe.SYSTEM_IDS_BY_NAME else None
        if system_id is None and system_name in Universe.SYSTEM_IDS_BY_UPPER_NAME:
            system_id = Universe.SYSTEM_IDS_BY_UPPER_NAME[system_name]
        return system_id

    @staticmethod
    def regionIdByName(region_name: str)->Optional[int]:
        return REGION_IDS_BY_NAME[region_name] if region_name in REGION_IDS_BY_NAME else None

    @staticmethod
    def regionNameById(region_id: int)->Optional[str]:
        return REGION_NAME_BY_ID[region_id] if region_id in REGION_NAME_BY_ID else None

    @staticmethod
    def constellationIdByName(constellation_name: str)->Optional[int]:
        return CONSTELLATION_IDS_BY_NAME[constellation_name] \
            if constellation_name in CONSTELLATION_IDS_BY_NAME else None

    @staticmethod
    def shipNames()->list[str]:
        return Universe.SHIP_NAMES

    @staticmethod
    def regionByID(region_id:int)->Optional[Region]:
        if region_id in Universe.REGIONS:
            return Universe.REGIONS_ID_OBJ[region_id]
        return Universe.REGIONS_ID_OBJ[region_id] if region_id in Universe.REGIONS else None

    @staticmethod
    def constellationByID(const_id:int)->Optional[Constellation]:
        return Universe.CONSTELLATIONS_ID_OBJS[const_id] if const_id in Universe.CONSTELLATIONS_ID_OBJS.keys() else None

    @staticmethod
    def stargatesBySystemID(system_id:int)->list[Stargate]:
        res = list()
        for _,stargate in Universe.STARGATES_ID_OBJ.items():
            if stargate.system_id  == system_id:
                res.append(stargate)
        return res

    @staticmethod
    def stargateByID(stargate_id)->Optional[Stargate]:
        return Universe.STARGATES_ID_OBJ[stargate_id] if stargate_id in Universe.STARGATES_ID_OBJ else None

    @staticmethod
    def regionIDFromSystemID(system_id:int)->Optional[int]:
        if system_id in Universe.SYSTEMS:
            return  Universe.SYSTEMS[system_id]["region_id"]
        else:
            return None

    @staticmethod
    def regionNameFromSystemID(system_id:int)->Optional[int]:
        region_id = Universe.regionIDFromSystemID(system_id)
        if region_id:
            return  Universe.REGIONS[region_id]["name"] if region_id in Universe.REGIONS.keys() else None
        else:
            return None

    @staticmethod
    def regionsFromRectangle(left:float,top:float,right:float,bottom:float)->list[int]:
        res = list()
        for key,rgn in Universe.REGIONS.items():
            if rgn["x"] > left and rgn["y"]> top and rgn["x"] < right and rgn["y"]< bottom:
                res.append(key)
        return res
