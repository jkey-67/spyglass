###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import datetime
import json
import time
import requests
import logging
import urllib
import aiohttp
import asyncio
import http.server
import webbrowser
from aiohttp import web
import base64
import hashlib
import secrets

from bs4 import BeautifulSoup
from vi.cache.cache import Cache

#ERROR = -1
#NOT_EXISTS = 0
#EXISTS = 1

def charnameToId(name,use_cache=True):
    """ Uses the EVE API to convert a character name to his ID
    """
    cacheKey = "_".join(("name", "id", name))
    cache = Cache()
    cached_id = cache.getFromCache(cacheKey)
    if use_cache and cached_id:
        return cached_id
    else:
        url = "https://esi.evetech.net/latest/search/?categories=character&datasource=tranquility&language=en-us&search={iname}&strict=true"
        content = requests.get(url.format(iname=name)).json()
        if "character" in content.keys():
            for idFound in content["character"]:
                url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=idFound)
                details = requests.get(url.format(name)).json()
                if "name" in details.keys():
                    name_found = details["name"]
                    if name_found.lower() == name.lower():
                        cache.putIntoCache(cacheKey, idFound, 60 * 60 * 24 * 365)
                        return idFound
        return None

def namesToIds(names):
    """ Uses the EVE API to convert a list of names to ids_to_names
        names: list of names
        returns a dict: key=name, value=id
    """
    if len(names) == 0:
        return {}
    data = {}
    apiCheckNames = set()
    cache = Cache()
    # do we have allready something in the cache?
    for name in names:
        cacheKey = "_".join(("id", "name", name))
        id = cache.getFromCache(cacheKey)
        if id:
            data[name] = id
        else:
            apiCheckNames.add(name)

    try:
        # not in cache? asking the EVE API
        if len(apiCheckNames) > 0:
            list_of_name = ""
            for name in names:
                if list_of_name != "":
                    list_of_name = list_of_name + ","
                list_of_name = list_of_name + "\"{}\"".format(name)
            # todo:change to esi
            url = "https://esi.evetech.net/latest/universe/ids/?datasource=tranquility"
            content = requests.post(url, data="[{}]".format(list_of_name)).json()
            if "characters" in content.keys():
                for char in content["characters"]:
                    data[char["name"]] = char["id"]
            # writing the cache
            for name in data:
                cacheKey = "_".join(("id", "name", name))
                cache.putIntoCache(cacheKey, data[name], 60 * 60 * 24 * 365)
    except Exception as e:
        logging.error("Exception during namesToIds: %s", e)
    return data

def getAllRegions():
    cache = Cache()
    all_systems = cache.getFromCache("list_of_all_systems")
    if all_systems != None:
        return eval(all_systems)
    else:
        url = "https://esi.evetech.net/latest/universe/regions/?datasource=tranquility"
        content = requests.get(url).json()
        cache.putIntoCache("list_of_all_systems", str(content))
        return content

def idsToNames(ids):
    """ Returns the names for ids
        ids = iterable list of ids
        returns a dict key = id, value = name
    """
    data = {}
    if len(ids) == 0:
        return data
    apiCheckIds = set()
    cache = Cache()

    # something allready in the cache?
    for id in ids:
        cacheKey = u"_".join(("name", "id", str(id)))
        name = cache.getFromCache(cacheKey)
        if name:
            data[id] = name
        else:
            apiCheckIds.add(id)
    if len(apiCheckIds)==0:
        return data

    try:
        list_of_ids = ""
        for id in apiCheckIds:
            if list_of_ids != "":
                list_of_ids = list_of_ids + ","
            list_of_ids = list_of_ids + str(id)
        url = "https://esi.evetech.net/latest/universe/names/?datasource=tranquility"
        content = requests.post(url, data="[{}]".format(list_of_ids)).json()
        if len(content) > 0:
            for elem in content:
                data[elem["id"]]=elem["name"]
            # and writing into cache
            for id in apiCheckIds:
                cacheKey = u"_".join(("name", "id", str(id)))
                cache.putIntoCache(cacheKey, data[id], 60 * 60 * 24 * 365)
    except Exception as e:
        logging.error("Exception during idsToNames: %s", e)
    return data


def getAvatarForPlayer(charname):
    """ Downlaoding the avatar for a player/character
        charname = name of the character
        returns None if something gone wrong
    """
    avatar = None
    try:
        charId = charnameToId(charname)
        if charId:
            imageUrl = "https://images.evetech.net/characters/{id}/portrait?tenant=tranquility&size={size}"
            avatar = requests.get(imageUrl.format(id=charId, size=64)).content
    except Exception as e:
        logging.error("Exception during getAvatarForPlayer: %s", e)
        avatar = None
    return avatar


def checkPlayername(charname):
    """ Checking on esi for an exiting exact player name
        returns 1 if exists, 0 if not and -1 if an error occured
    """
    try:
        baseUrl = "https://esi.evetech.net/latest/search/?categories=character&datasource=tranquility&language=en&search={charname}&strict=true"
        content = requests.get(baseUrl.format(charname=charname)).json()
        if "character" in content.keys():
            if len(content["character"]):
                return 1
            else:
                return 0
        else:
            return -1
    except Exception as e:
        logging.error("Exception on checkPlayername: %s", e)
    return -1


def currentEveTime():
    """ Returns the current eve-time as a datetime.datetime
    """
    return datetime.datetime.utcnow()


def eveEpoch():
    """ Returns the seconds since epoch in eve timezone
    """
    return time.mktime(datetime.datetime.utcnow().timetuple())

def getCharinfoForCharId(charId,use_cache=True):
    cacheKey = u"_".join(("playerinfo_id_", str(charId)))
    cache = Cache()
    char_info = cache.getFromCache(cacheKey)
    if use_cache and char_info is not None:
        char_info = eval(char_info)
    else:
        try:
            charId = int(charId)
            url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=charId)
            content = requests.get(url).text
            char_info = eval(content)
            # should be valid for up to three days
            cache.putIntoCache(cacheKey, content, 60*60*24*3)
        except requests.exceptions.RequestException as e:
            # We get a 400 when we pass non-pilot names for KOS check so fail silently for that one only
            if (e.response.status_code != 400):
                logging.error("Exception during getCharinfoForCharId: %s", str(e))
    return char_info

def getCorpidsForCharId(charId,use_cache=True):
    """ Returns a list with the ids if the corporation history of a charId
        returns a list of only the corp ids
    """
    cacheKey = u"_".join(("corp_history_id_", str(charId)))
    cache = Cache()
    corp_ids = cache.getFromCache(cacheKey)
    if use_cache and corp_ids is not None:
        corp_ids = eval(corp_ids)
    else:
        try:
            charId = int(charId)
            url = "https://esi.evetech.net/latest/characters/{id}/corporationhistory/?datasource=tranquility".format(id=charId)
            content = requests.get(url).text
            corp_ids = eval(content)
            cache.putIntoCache(cacheKey, content)
        except requests.exceptions.RequestException as e:
            # We get a 400 when we pass non-pilot names for KOS check so fail silently for that one only
            if (e.response.status_code != 400):
                logging.error("Exception during getCharinfoForCharId: %s", str(e))
    id_list = list()
    for elem in corp_ids:
        id_list.append(elem["corporation_id"])
    return id_list

def getCurrentCorpForCharId(charId,use_cache=True):
    """ Returns the ID of the players current corporation.
    """
    info = getCharinfoForCharId(charId,use_cache)
    if info and "corporation_id" in info.keys():
        return info["corporation_id"]
    else:
        logging.error("Unable to get corporation_id of char id:{}".format(charId))
        return None

def getSystemStatistics():
    """ Reads the informations for all solarsystems from the EVE API
        Reads a dict like:
            systemid: "jumps", "shipkills", "factionkills", "podkills"
    """
    data = {}
    systemData = {}
    cache = Cache()
    # first the data for the jumps
    cacheKey = "jumpstatistic"
    jumpData = cache.getFromCache(cacheKey)

    try:
        if jumpData is None:
            jumpData = {}
            url = "https://esi.evetech.net/latest/universe/system_jumps/?datasource=tranquility"
            resp = requests.get(url).json()
            for row in resp:
                jumpData[int(row["system_id"])] = int(row["ship_jumps"])

            cache.putIntoCache(cacheKey, json.dumps(jumpData), 60)
        else:
            jumpData = json.loads(jumpData)

        # now the further data
        cacheKey = "systemstatistic"
        systemData = cache.getFromCache(cacheKey)

        if systemData is None:
            systemData = {}
            url = "https://esi.evetech.net/latest/universe/system_kills/?datasource=tranquility"
            resp = requests.get(url).json()
            for row in resp:
                systemData[int(row["system_id"])] = {"ship": int(row["ship_kills"]),
                                                        "faction": int(row["npc_kills"]),
                                                        "pod": int(row["pod_kills"])}

            cache.putIntoCache(cacheKey, json.dumps(systemData), 60 )
        else:
            systemData = json.loads(systemData)
    except Exception as e:
        logging.error("Exception during getSystemStatistics: : %s", e)

    # We collected all data (or loaded them from cache) - now zip it together
    for i, v in jumpData.items():
        i = int(i)
        if i not in data:
            data[i] = {"shipkills": 0, "factionkills": 0, "podkills": 0}
        data[i]["jumps"] = v
    for i, v in systemData.items():
        i = int(i)
        if i not in data:
            data[i] = {"jumps": 0}
        data[i]["shipkills"] = v["ship"] if "ship" in v else 0
        data[i]["factionkills"] = v["faction"] if "faction" in v else 0
        data[i]["podkills"] = v["pod"] if "pod" in v else 0
    return data

def secondsTillDowntime():
    """ Return the seconds till the next downtime"""
    now = currentEveTime()
    target = now
    if now.hour > 11:
        target = target + datetime.timedelta(1)
    target = datetime.datetime(target.year, target.month, target.day, 11, 0, 0, 0)
    delta = target - now
    return delta.seconds

class MyApiServer(http.server.BaseHTTPRequestHandler):
    """http server to get the redirected login message
    """
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>Spyglass API Registration</title></head>".encode("utf-8"))
        self.wfile.write("<body onload=\"closePage()\"><p>This is a test.</p>".encode("utf-8"))
        self.wfile.write("<script>function closePage(){self.close();}</script>".encode("utf-8"))
        self.wfile.write("</body></html>".encode("utf-8"))
        self.wfile.close()
        try:
            code = self.requestline.split(" ")[1]
            pos_code = code.find("code=")
            pos_state = code.find("&state=")
            self.server.api_code=code[pos_code + 5:pos_state]
            self.server.api_state=code[pos_state+6:]
            self.server.server_close()
        except Exception as e:
            logging.error("Exception during MyApiServer: %s", e)
            self.server.api_code = None

def getApiKey(client_param)->str:
    """ Queries the eve-online api key valid for one eve online account,
        using http://localhost:8182/oauth-callback as application defined
        callback from inside the webb browser
        params client_id, scope and state see esi-docs
    """
    hash=hashlib.sha256()
    hash.update(client_param["random"])
    digs=hash.digest()
    code_challenge = base64.urlsafe_b64encode(digs).decode().replace("=", "")
    params = {
        "response_type": "code",
        "redirect_uri": "http://localhost:8182/oauth-callback",
        "client_id": client_param["client_id"],
        "scope": client_param["scope"],
        "state": client_param["state"],
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    string_params = urllib.parse.urlencode(params)
    webbrowser.open_new("https://login.eveonline.com/v2/oauth/authorize?{}".format(string_params))
    webserver = http.server.HTTPServer(("localhost", 8182), MyApiServer)
    webserver.handle_request()
    api = webserver.api_code
    del webserver
    return api

def getAccessToken(client_param,auth_code:str,add_headers={})->str:
    """ gets the access token from the application logging
        fills the cache wit valid login data
    """
    form_values={
        "grant_type": "authorization_code",
        "client_id": client_param["client_id"],
        "code": auth_code,
        "code_verifier":  client_param["random"]
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    if add_headers:
        headers.update(add_headers)
    res = requests.post(
        "https://login.eveonline.com/v2/oauth/token",
        data=form_values,
        headers=headers,
    )
    if res.status_code == 200:
        aut_call = res.json()
        header={
            "Authorization": "{} {}".format(aut_call["token_type"],aut_call["access_token"]),
        }
        res = requests.get( "https://login.eveonline.com/oauth/verify",headers=header)
        res.raise_for_status()
        char_id = res.json()
        cache = Cache()
        char_id.update(aut_call)
        cacheKey = "_".join(("api_key", "character_name", char_id["CharacterName"]))
        cache.putIntoCache(cacheKey, str(char_id))
        cache.putIntoCache("api_char_name", char_id["CharacterName"])
        return char_id["CharacterName"];
    else:
        res.raise_for_status()
    return None

def openWithEveonline()->str:
    """perform a api key request and updates the cache on case of an positive response
        returns the selected user name from the login
    """
    client_param = {
        "client_id": "9eaf6cb03a9649998b2bad63b9e9fa8e",
        "scope": "esi-ui.write_waypoint.v1 esi-universe.read_structures.v1 esi-search.search_structures.v1",
        "random": base64.urlsafe_b64encode(secrets.token_bytes(32)),
        "state": base64.urlsafe_b64encode(secrets.token_bytes(8))
    }
    auth_code = getApiKey(client_param)
    res = getAccessToken(client_param, auth_code)

class ApiKey(object):
    def __init__(self, dictionary):
        self.__dict__=dictionary
        #self.CharacterID = None
        #self.CharacterName = None
        self.valid_until = None
        self.expires_in = None

    def update(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)

def getTokenOfChar(char_name:str):
    """gets  the api key for chae_name from the cache
    """
    cache = Cache()
    cache_key = "_".join(("api_key", "character_name", char_name))
    char_data = cache.getFromCache(cache_key)
    if char_data:
        return ApiKey(eval(char_data))
    else:
        return None

def refreshToken(params:ApiKey):
    """ refreshes the token using the previously acquired data structure from the cache
        if succeeded with result 200 the cache will be updated too
    """
    data = {
        "grant_type":"refresh_token",
        "refresh_token": params.refresh_token,
        "client_id": "9eaf6cb03a9649998b2bad63b9e9fa8e",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    req_post = requests.post("https://login.eveonline.com/v2/oauth/token", data=data, headers=headers)
    req_post.raise_for_status()
    ref_token = req_post.json()
    params.update(ref_token)
    params.valid_until = time.time()+params.expires_in
    cache = Cache()
    cache_key = "_".join(("api_key", "character_name", params.CharacterName))
    cache.putIntoCache(cache_key, params.__dict__.__str__())
    return params

def checkTokenTimeLine(param:ApiKey):
    """ double check the api timestamp, if expired the parm set will be updated
    """
    if param.valid_until != None and param.valid_until > time.time():
        return param
    else:
        return refreshToken(param)

def sendTokenRequest(form_values, add_headers={}):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    if add_headers:
        headers.update(add_headers)

    res = requests.post(
        "https://login.eveonline.com/v2/oauth/token",
        data=form_values,
        headers=headers,
    )

    print("Request sent to URL {} with headers {} and form values: "
          "{}\n".format(res.url, headers, form_values))
    res.raise_for_status()
    return res


def setDestination(nameChar:str,idSystem:int,beginning=True, clear_all=True):
    token = checkTokenTimeLine(getTokenOfChar(nameChar))
    if token:
        route = {
            "add_to_beginning": beginning,
            "clear_other_waypoints": clear_all,
            "datasource": "tranquility",
            "destination_id": idSystem,
            "token": token.access_token,
        }
        req = "https://esi.evetech.net/latest/ui/autopilot/waypoint/?{}".format(urllib.parse.urlencode(route))
        requests.post(req).raise_for_status()

def getRouteFromEveOnline( jumpGates,src,dst):
    """build rout respecting jump bridges
        returns the list of systems to travel to
    """
    route_elems = ""
    for elem in jumpGates:
        if route_elems != "":
            route_elems = route_elems + ","
        route_elems = route_elems + "{}|{}".format(elem[0], elem[1])

    req = "https://esi.evetech.net/v1/route/{}/{}/?connections={}".format(src, dst, route_elems)
    res = requests.get(req)
    res.raise_for_status()
    return eval(res.text)

def getAllStructures():
    req="https://esi.evetech.net/latest/universe/structures/?datasource=tranquility"
    res = requests.get(req)
    res.raise_for_status()
    return eval(res.text)

def getStructures(nameChar:str,id_structure:int):
    token = checkTokenTimeLine(getTokenOfChar(nameChar))
    req = "https://esi.evetech.net/v1/universe/structures/{}/?datasource=tranquility&token={}".format(id_structure,token.access_token)
    res = requests.get(req)
    # res.raise_for_status()
    print(res.text)
    return eval(res.text)

class JumpBridge(object):
    def __init__(self, name:str, structureId:int, systemId:int):
        tok = name.split(" ")
        self.src_system_name = tok[0]
        self.dst_system_name = tok[2]
        self.name = name
        self.structureId = structureId
        self.systemId = systemId
        self.paired=False
        self.links = 0

def sanityCheckGates( gates ):
    """ grant that all item of gates builds valid pairs of jump bridges src<->dst and also dst<->src
        all other items will be removed
    """
    for gate in gates:
        for elem in gates:
            if (gate.src_system_name == elem.dst_system_name) and (gate.dst_system_name == elem.src_system_name):
                gate.paired = True
                elem.paired = True

    for gate in gates:
        if not gate.paired:
            gates.remove(gate)
    return gates

def countCheckGates( gates ):
    for gate in gates:
        for elem in gates:
            if (gate.src_system_name == elem.src_system_name) or (gate.src_system_name == elem.dst_system_name):
                gate.links = gate.links+1

def getAllJumpGates(nameChar:str,systemName=""):
    """ updates all jump bridge data via api searching for names which have a substring  %20%C2%BB%20 means " >> "
    """
    token = checkTokenTimeLine(getTokenOfChar(nameChar))
    req = "https://esi.evetech.net/v3/characters/{id}/search/?datasource=tranquility&categories=structure&search={sys}%20%C2%BB%20&token={tok}".format(id=token.CharacterID, tok=token.access_token,sys=systemName)
    res = requests.get(req)
    res.raise_for_status()
    structs = eval(res.text)
    gates = list()
    if token:
        for id_structure in structs["structure"]:
            req = "https://esi.evetech.net/v1/universe/structures/{}/?datasource=tranquility&token={}".format(id_structure, token.access_token)
            res = requests.get(req)
            #res.raise_for_status()
            if res.text.find("35841") != -1:
                item = eval(res.text)
                if item["type_id"] == 35841:
                    gates.append(JumpBridge(name=item["name"], systemId=item["solar_system_id"], structureId=id_structure))
            else:
                print(" not valid")
    #gates=sanityCheckGates(gates)
    #countCheckGates(gates)
    return gates

def writeGatestToFile(gates, filename="jb.txt"):
    gates_list = list()
    with open(filename, "w")as gf:
        for gate in gates:
            s_t_d = "{} <-> {}".format(gate.src_system_name, gate.dst_system_name)
            d_t_s = "{} <-> {}".format(gate.dst_system_name, gate.src_system_name)
            if (  not s_t_d in gates_list) and (not d_t_s in gates_list):
                gf.write(s_t_d + "\n")
                gates_list.append(s_t_d)
        gf.close()


def hasAnsiblex( sys )->bool:
    return False

def applyRouteToEveOnline(nameChar, jumpList):
    for idSystem in jumpList:
        if hasAnsiblex(idSystem):
            pass
        else:
            setDestination(nameChar, idSystem, beginning=False, clear_all=False)

SHIPNAMES = (u'ABADDON', u'ABSOLUTION', u'AEON', u'AMARR SHUTTLE', u'ANATHEMA', u'ANSHAR', u'APOCALYPSE',
             u'APOCALYPSE IMPERIAL ISSUE', u'APOCALYPSE NAVY ISSUE', u'APOTHEOSIS', u'ARAZU', u'ARBITRATOR', u'ARCHON',
             u'ARES', u'ARK', u'ARMAGEDDON', u'ARMAGEDDON IMPERIAL ISSUE', u'ASHIMMU', u'ASTARTE', u'ATRON', u'AUGOROR',
             u'AUGOROR NAVY ISSUE', u'AVATAR', u'BADGER', u'BADGER MARK II', u'BANTAM', u'BASILISK', u'BELLICOSE',
             u'BESTOWER', u'BHAALGORN', u'BLACKBIRD', u'BREACHER', u'BROADSWORD', u'BRUTIX', u'BURST', u'BUSTARD',
             u'BUZZARD', u'CONCORD ARMY BATTLESHIP', u'CONCORD ARMY CRUISER', u'CONCORD ARMY FRIGATE',
             u'CONCORD POLICE BATTLESHIP', u'CONCORD POLICE CRUISER', u'CONCORD POLICE FRIGATE',
             u'CONCORD SWAT BATTLESHIP', u'CONCORD SWAT CRUISER', u'CONCORD SWAT FRIGATE',
             u'CONCORD SPECIAL OPS BATTLESHIP', u'CONCORD SPECIAL OPS CRUISER', u'CONCORD SPECIAL OPS FRIGATE',
             u'CALDARI NAVY HOOKBILL', u'CALDARI SHUTTLE', u'CARACAL', u'CARACAL NAVY ISSUE', u'CATALYST', u'CELESTIS',
             u'CERBERUS', u'CHARON', u'CHEETAH', u'CHIMERA', u'CLAW', u'CLAYMORE', u'COERCER', u'CONDOR', u'CORMORANT',
             u'COVETOR', u'CRANE', u'CROW', u'CRUCIFIER', u'CRUOR', u'CRUSADER', u'CURSE', u'CYCLONE', u'CYNABAL',
             u'DAMNATION', u'DAREDEVIL', u'DEIMOS', u'DEVOTER', u'DOMINIX', u'DRAKE', u'DRAMIEL', u'EAGLE', u'EIDOLON',
             u'ENIGMA', u'ENYO', u'EOS', u'EREBUS', u'ERIS', u'EXECUTIONER', u'EXEQUROR', u'EXEQUROR NAVY ISSUE',
             u'FALCON', u'FEDERATION NAVY COMET', u'FENRIR', u'FEROX', u'FLYCATCHER', u'GALLENTE SHUTTLE', u'GILA',
             u'GOLD MAGNATE', u'GOLEM', u'GRIFFIN', u'GUARDIAN', u'HARBINGER', u'HARPY', u'HAWK', u'HEL', u'HELIOS',
             u'HERETIC', u'HERON', u'HOARDER', u'HOUND', u'HUGINN', u'HULK', u'HURRICANE', u'HYENA', u'HYPERION',
             u'IBIS', u'IMICUS', u'IMPAIROR', u'IMPEL', u'IMPERIAL NAVY SLICER', u'INCURSUS', u'ISHKUR', u'ISHTAR',
             u'ITERON', u'ITERON MARK II', u'ITERON MARK III', u'ITERON MARK IV', u'ITERON MARK V', u'JAGUAR', u'KERES',
             u'KESTREL', u'KITSUNE', u'KRONOS', u'LACHESIS', u'LEVIATHAN', u'MACHARIEL', u'MACKINAW', u'MAELSTROM',
             u'MAGNATE', u'MALEDICTION', u'MALLER', u'MAMMOTH', u'MANTICORE', u'MASTODON', u'MAULUS', u'MEGATHRON',
             u'MEGATHRON FEDERATE ISSUE', u'MEGATHRON NAVY ISSUE', u'MERLIN', u'MINMATAR SHUTTLE', u'MOA', u'MOROS',
             u'MUNINN', u'MYRMIDON', u'NAGLFAR', u'NAVITAS', u'NEMESIS', u'NIDHOGGUR', u'NIGHTHAWK', u'NIGHTMARE',
             u'NOMAD', u'NYX', u'OBELISK', u'OCCATOR', u'OMEN', u'OMEN NAVY ISSUE', u'ONEIROS', u'ONYX',
             u'OPUX DRAGOON YACHT', u'OPUX LUXURY YACHT', u'ORACLE', u'ORCA', u'OSPREY', u'OSPREY NAVY ISSUE',
             u'PALADIN', u'PANTHER', u'PHANTASM', u'PHANTOM', u'PHOBOS', u'PHOENIX', u'PILGRIM', u'POLARIS CENTURION',
             u'POLARIS INSPECTOR', u'POLARIS LEGATUS', u'PROBE', u'PROCURER', u'PROPHECY', u'PRORATOR', u'PROVIDENCE',
             u'PROWLER', u'PUNISHER', u'PURIFIER', u'RAGNAROK', u'RAPIER', u'RAPTOR', u'RATTLESNAKE', u'RAVEN',
             u'RAVEN NAVY ISSUE', u'RAVEN STATE ISSUE', u'REAPER', u'REDEEMER', u'REPUBLIC FLEET FIRETAIL',
             u'RETRIBUTION', u'RETRIEVER', u'REVELATION', u'RHEA', u'RIFTER', u'ROKH', u'ROOK', u'RORQUAL', u'RUPTURE',
             u'SABRE', u'SACRILEGE', u'SCIMITAR', u'SCORPION', u'SCYTHE', u'SCYTHE FLEET ISSUE', u'SENTINEL', u'SIGIL',
             u'SILVER MAGNATE', u'SIN', u'SKIFF', u'SLASHER', u'SLEIPNIR', u'SPECTER', u'STABBER',
             u'STABBER FLEET ISSUE', u'STILETTO', u'SUCCUBUS', u'TARANIS', u'TEMPEST', u'TEMPEST FLEET ISSUE',
             u'TEMPEST TRIBAL ISSUE', u'THANATOS', u'THORAX', u'THRASHER', u'TORMENTOR', u'TRISTAN', u'TYPHOON',
             u'VAGABOND', u'VARGUR', u'VELATOR', u'VENGEANCE', u'VEXOR', u'VEXOR NAVY ISSUE', u'VIATOR', u'VIGIL',
             u'VIGILANT', u'VINDICATOR', u'VISITANT', u'VULTURE', u'WIDOW', u'WOLF', u'WORM', u'WRAITH', u'WREATHE',
             u'WYVERN', u'ZEALOT', u'CAPSULE',)
SHIPNAMES = sorted(SHIPNAMES, key=lambda x: len(x), reverse=True)

NPC_CORPS = (u'Republic Justice Department', u'House of Records', u'24th Imperial Crusade', u'Template:NPC corporation',
             u'Khanid Works', u'Caldari Steel', u'School of Applied Knowledge', u'NOH Recruitment Center',
             u'Sarum Family', u'Impro', u'Guristas', u'Carthum Conglomerate', u'Secure Commerce Commission',
             u'Amarr Trade Registry', u'Anonymous', u'Federal Defence Union', u'Federal Freight', u'Ardishapur Family',
             u'Thukker Mix', u'Sebiestor tribe', u'Core Complexion Inc.', u'Federal Navy Academy', u'Dominations',
             u'Ishukone Watch', u'Kaalakiota Corporation', u'Nurtura', u'Center for Advanced Studies', u'CONCORD',
             u'Ammatar Consulate', u'HZO Refinery', u'Joint Harvesting', u'Caldari Funds Unlimited', u'Propel Dynamics',
             u'Caldari Navy', u'Amarr Navy', u'Amarr Certified News', u'Serpentis Corporation', u'CreoDron',
             u'Society of Conscious Thought', u'Shapeset', u'Kor-Azor Family', u'Khanid Transport',
             u'Imperial Chancellor', u'Rapid Assembly', u'Khanid Innovation', u'Combined Harvest',
             u'Peace and Order Unit', u'The Leisure Group', u'CBD Sell Division', u'DED', u'Six Kin Development',
             u'Zero-G Research Firm', u'Defiants', u'Noble Appliances', u'Guristas Production', u'Intaki Space Police',
             u'Spacelane Patrol', u'User talk:ISD Crystal Carbonide', u'Caldari Provisions', u'Brutor tribe',
             u'True Power', u'Nefantar Miner Association', u'Garoun Investment Bank', u'FedMart', u'Prosper',
             u'Inherent Implants', u'Chief Executive Panel', u'Top Down', u'Federation Customs',
             u'Lai Dai Protection Service', u'Roden Shipyards', u'Wiyrkomi Peace Corps', u'Allotek Industries',
             u'Minedrill', u'Court Chamberlain', u'Intaki Syndicate', u'Caldari Constructions',
             u'State and Region Bank', u'Amarr Civil Service', u'Pend Insurance', u'Zainou', u'Material Institute',
             u'Republic Fleet', u'Intaki Bank', u'Hyasyoda Corporation', u'Nugoeihuvi Corporation', u'Modern Finances',
             u'Bank of Luminaire', u'Ministry of War', u'Genolution', u'Pator Tech School', u'Hedion University',
             u'Kador Family', u'Ducia Foundry', u'Prompt Delivery', u'Trust Partners', u'Material Acquisition',
             u'Jovian Directorate', u'DUST 514 NPC Corporations', u'Ministry of Assessment', u'Expert Distribution',
             u'Ishukone Corporation', u'Caldari Business Tribunal', u'The Scope', u'Eifyr and Co.',
             u'Jovian directorate', u'Lai Dai Corporation', u'Chemal Tech', u'CBD Corporation', u'Internal Security',
             u'Salvation Angels', u'TransStellar Shipping', u'InterBus', u'Outer Ring Excavations',
             u'Tribal Liberation Force', u'Impetus', u'Intaki Commerce', u'University of Caille', u'Home Guard',
             u'The Draconis Family', u'The Sanctuary', u'Republic University', u'Federal Intelligence Office',
             u'Egonics Inc.', u'Native Freshfood', u'Republic Security Services', u'Wiyrkomi Corporation',
             u'Sukuuvestaa Corporation', u'Vherokior tribe', u'Republic Parliament', u'Ytiri', u'Mercantile Club',
             u'Civic Court', u'Imperial Academy', u'Tash-Murkon Family', u'Viziam', u'Ammatar Fleet',
             u'Urban Management', u'Royal Amarr Institute', u'Echelon Entertainment', u'Archangels',
             u'Poteque Pharmaceuticals', u'Imperial Armaments', u'Academy of Aggressive Behaviour',
             u'Duvolle Laboratories', u'Ministry of Internal Order', u'Quafe Company', u'Serpentis Inquest',
             u'True Creations', u'Science and Trade Institute', u'Further Foodstuffs', u'Poksu Mineral Group',
             u'Astral Mining Inc.', u'Krusual tribe', u'Blood Raiders', u'Amarr Constructions', u'Federation Navy',
             u'Inner Circle', u'State War Academy', u'Zoar and Sons', u'Boundless Creation', u'Guardian Angels',
             u'Food Relief', u'Royal Khanid Navy', u'Imperial Shipment', u'Perkone', u'Federal Administration',
             u'Emperor Family', u'Inner Zone Shipping', u'Theology Council', u'Aliastra', u'Republic Military School',
             u'Freedom Extension', u'Sisters of EVE', u'President', u'Expert Housing', u'Deep Core Mining Inc.',
             u'Senate', u"Mordu's Legion", u'State Protectorate', u'Jove Navy', u'X-Sense', u'Corporate Police Force',
             u'Minmatar Mining Corporation', u'Supreme Court')


# The main application for testing
if __name__ == "__main__":
    #see https://developers.eveonline.com/applications/details/69202
    #see https://github.com/esi/esi-docs/blob/master/examples/python/sso/esi_oauth_native.py
    #see https://docs.esi.evetech.net/docs/sso/native_sso_flow.html
    #auth = esipysi.EsiAuth(client_id="9eaf6cb03a9649998b2bad63b9e9fa8e")
    #key_secret = '{}:{}'.format("9eaf6cb03a9649998b2bad63b9e9fa8e", "QrTL5CyPcXKpKMTtL65iR1dLX5nFPtz75lChjSpl").encode('ascii')
    #b64_encoded_key = base64.b64encode(key_secret)
    #openWithEveonline()
    #gate = getStructures("nele McCool", 1035408540831)
    #[14:39:29] nele McCool > <url=showinfo:35841//1035408540831>UR-E46 » Y-CWQY - gate --</url>
    #1034954775591 x nele McCool
    #setDestination("nele McCool", 1035408540831)  # ansiblex UR - E46
    sysnames = idsToNames(getAllRegions())
    some = ["{}".format(itm) for key,itm in sysnames.items()]
    id = charnameToId("nele McCool",False)
    corp=getCurrentCorpForCharId(1350114619,False)
    nase=namesToIds({"nele McCool", "G-M4GK"})
    res = getCorpidsForCharId(charnameToId("nele McCool"))
    res = getCharinfoForCharId(charnameToId("nele McCool"))
    gates = getAllJumpGates("nele McCool", "G-M4GK")
    setDestination("nele McCool", 1035408540831)  # ansiblex
    setDestination("nele McCool", 1034969570497)  # ansiblex
    setDestination("nele McCool", 1034954775591)  # ansiblex
    jumpGates=[[30004935,30004961]]
    src = 30004935
    dst = 30004961
    route = getRouteFromEveOnline( jumpGates, src,dst)
    applyRouteToEveOnline( "nele McCool",route)
    setDestination("nele McCool", 0, True, True)

    setDestination("nele McCool",1035408540831)#ansiblex
    setDestination("nele McCool",30003770)
    res = getTokenOfChar( "MrX")
    exit(1)
    client_param = {
        "client_id": "9eaf6cb03a9649998b2bad63b9e9fa8e",
        "scope": "esi-ui.write_waypoint.v1",
        "random": base64.urlsafe_b64encode(secrets.token_bytes(32)),
        "state": base64.urlsafe_b64encode(secrets.token_bytes(8))
    }
    auth_code = getApiKey(client_param)
    res = getAccessToken(client_param, auth_code)
    exit(1)
    res = getCharinfoForCharId( charnameToId( "Nele McCool" ))

    res = getAvatarForPlayer("Dae\'M");
    res = checkPlayername( "Nele McCool" )
    res = getAvatarForPlayer( "Nele McCool")
    res = checkPlayername("Rovengard Ogaster")
    res = checkPlayername("121%2011%2011%2011")
    res = getAvatarForPlayer("121%2011%2011%2011")

