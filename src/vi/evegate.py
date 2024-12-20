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

import datetime
import locale
import json
import os.path
import time
import parse
import threading

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, QUrl, QFile, QIODevice
from PySide6.QtCore import Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from packaging import version

import queue
import requests
from requests.sessions import Session
from threading import local
import logging
import urllib.parse
import http.server
import webbrowser
import base64
import hashlib
import secrets
from typing import Optional
from enum import Enum
from eve_api_key import APPLICATION_CLIENTS_ID
from vi.cache.cache import Cache
from vi.version import VERSION
from vi.universe import Universe
from vi.universe.routeplanner import RoutPlanner

thread_local = local()

ERROR = -1
NOT_EXISTS = 0
EXISTS = 1


class ApiKey(object):
    def __init__(self, dictionary):
        self.__dict__ = dictionary
        if not hasattr(self, 'valid_until'):
            self.access_token = None
        if not hasattr(self, 'valid_until'):
            self.valid_until = None
        if not hasattr(self, 'expires_in'):
            self.expires_in = None
        if not hasattr(self, 'refresh_token'):
            self.refresh_token = None
        if not hasattr(self, 'CharacterName'):
            self.CharacterName = None
        if not hasattr(self, 'CharacterID'):
            self.CharacterID = None

    def update(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)


def getSession() -> Session:
    if not hasattr(thread_local, 'session'):
        thread_local.session = requests.Session()  # Create a new Session if not exists
        thread_local.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json"
             })
    return thread_local.session


def _logResponseError(response):
    logging.error('ESI-Error {}, Info "{}", url "{}", response text: "{}"'.format(
        response.status_code, response.reason, response.url, response.text), stacklevel=2)


# todo :  split the cache from esi functionality

def setEsiCharName(name):
    """
    Sets the name of the current active api char to sqlite cache.

    Args:
        name(str):name of the active esi character

    Returns:
        str: Name of the current char from cache as string, or None
    """
    if name and name != "":
        Cache().putIntoCache("api_char_name", name)


def esiCharName() -> Optional[str]:
    """
    Gets the name of the current active api char from the sqlite cache.

    Args: None

    Returns:
        str: Name of the current char from cache as string, or None
    """
    res_name = Cache().getFromCache("api_char_name", True)
    if res_name is None or res_name == "" or res_name not in Cache().getAPICharNames():
        res_name = Cache().getAPICharNames()
        if res_name and len(res_name):
            setEsiCharName(res_name[0])
            Cache().putIntoCache("api_char_name", res_name[0])
            return res_name[0]
        else:
            Cache().removeFromCache("api_char_name")
            return None
    else:
        return res_name


def secondUntilExpire(response, default: int = 3600) -> int:
    """
        Returns the second until expire from the html response header as int
    Args:
        response:
        default: 1h as default

    Returns:
        int: Seconds that can be used for caching, or 3600 as default
    """
    response_keys = response.headers.keys()
    if "Expires" in response_keys:
        expires = response.headers["Expires"]
        locale.setlocale(locale.LC_TIME, 'en_US')
        res_time = datetime.datetime.strptime(expires, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=datetime.timezone.utc)
        utc_time = datetime.datetime.now(datetime.timezone.utc)
        return (res_time - utc_time).seconds
    else:
        return default


def esiStatus() -> dict:
    """
    Request EVE Server status
    Returns:
        dict: status of EVE-Online

    """
    url = "https://esi.evetech.net/latest/status/?datasource=tranquility"
    response = getSession().get(url=url)
    if response.status_code == 200:
        return response.json()
    else:
        _logResponseError(response)
        response.raise_for_status()


def esiCharNameToId(char_name: str, use_outdated=False, use_cache=True) -> Optional[int]:
    """ Uses the EVE API to convert a character name to his ID.

    Args:
        char_name(str):character name to convert
        use_outdated(bool):if True, the cache timestamp will be ignored
        use_cache(bool):
    Returns:
        int:id of the character name or None
    """
    cache_key = "_".join(("name", "id", char_name))
    cache = Cache()
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data:
        return cache_data
    else:
        content = esiUniverseIds({char_name})
        if "characters" in content.keys():
            for idFound in content["characters"]:
                url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=idFound["id"])
                response = getSession().get(url.format(char_name))
                if response.status_code == 200:
                    details = response.json()
                    if "name" in details.keys():
                        name_found = details["name"]
                        if name_found.lower() == char_name.lower():
                            cache.putIntoCache(cache_key, idFound["id"], secondUntilExpire(response))
                            return idFound["id"]
                else:
                    _logResponseError(response)
                    response.raise_for_status()
    return None


def esiUniverseIds(names, use_outdated=False, use_cache=False) -> dict:
    """ Uses the EVE API to convert a list of names to ids_to_names

    Args:
        names(list(str)): names list of names
        use_outdated(bool): if True the cache timestamp will be ignored
        use_cache:

    Returns:
             dict: holding list of dict of the same type : key=name, value=id
    """
    if len(names) == 0:
        return {}
    data = {}
    api_check_names = set()
    cache = Cache()
    for name in names:
        cache_key = "_".join(("ids", "dicts", name))
        cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
        if cache_data:
            for key, items in json.loads(cache_data).items():
                for item in items:
                    if key in data.keys():
                        data[key].append(item)
                    else:
                        data[key] = [item]

        else:
            api_check_names.add(name)

    try:
        if len(api_check_names) > 0:
            list_of_name = ""
            for name in api_check_names:
                if list_of_name != "":
                    list_of_name = list_of_name + ","
                list_of_name = list_of_name + '"{}"'.format(name)
            post_url = "https://esi.evetech.net/latest/universe/ids/?datasource=tranquility"
            post_data = "[{}]".format(list_of_name)
            response = getSession().post(post_url, data=post_data)
            if response.status_code == 200:
                content = response.json()
                with Cache() as cache:
                    for key, items in content.items():
                        for item in items:
                            cache_data = dict()
                            cache_data[key] = [item]
                            cache_key = "_".join(("ids", "dicts", item["name"]))
                            cache.putIntoCacheNoLock(cache_key, json.dumps(cache_data))
                            if key in data.keys():
                                data[key].append(item)
                            else:
                                data[key] = [item]
                    cache.con.commit()
                return data
            else:
                logging.error("ESI-Error %i : '%s' url: %s data=%s",
                              response.status_code, response.reason, response.url, post_data)
    except Exception as e:
        logging.error("Exception during namesToIds: %s", e)
    return data


def esiUniverseNames(ids: set, use_outdated=False):
    """ Returns the names for a list of ids

        Args:
            ids(set): set of ids to search
            use_outdated(bool): if True the cache timestamp will be ignored

        Returns:
              dict:dict  key = id, value = name
    """
    data = {}
    if len(ids) == 0:
        return data
    api_check_ids = list()
    cache = Cache()

    # something already in the cache?
    for checked_id in ids:
        cache_key = u"_".join(("name", "id", str(checked_id)))
        cache_data = cache.getFromCache(cache_key, use_outdated)
        if cache_data:
            data[checked_id] = cache_data
        else:
            api_check_ids.append(checked_id)

    if len(api_check_ids) == 0:
        return data

    try:
        list_of_ids = ""
        for checked_id in list(set(api_check_ids[0:999])):
            if list_of_ids != "":
                list_of_ids = list_of_ids + ","
            list_of_ids = list_of_ids + str(checked_id)
        url = "https://esi.evetech.net/latest/universe/names/?datasource=tranquility"
        response = getSession().post(url, data="[{}]".format(list_of_ids))
        if response.status_code != 200:
            _logResponseError(response)
            response.raise_for_status()
        content = response.json()
        if len(content) > 0:
            for elem in content:
                data[elem["id"]] = elem["name"]
            # and writing into cache
            with Cache() as cache:
                for checked_id in api_check_ids:
                    cache_key = u"_".join(("name", "id", str(checked_id)))
                    if checked_id in data.keys():
                        # todo check secondUntilExpire(response)
                        cache.putIntoCacheNoLock(cache_key, data[int(checked_id)], 60 * 60 * 24 * 365)
                cache.con.commit()
        if len(api_check_ids) > 1000:
            return esiUniverseNames(ids, use_outdated)
    except Exception as e:
        logging.error("Exception during idsToNames: %s", e)
    return data


def esiDogmaAttributes(attribute_id: int, use_outdated=False, lang="en", use_cache=True):
    """ Returns the names for a list of ids

        Args:
            attribute_id(set): set of ids to search
            use_outdated(bool): if True the cache timestamp will be ignored
            use_cache(bool): use data from cache
            lang: language used

        Returns:
              dict:dict  key = id, value = name
    """
    cache = Cache()

    # something already in the cache?
    cache_key = u"_".join(("attribute", "id", str(attribute_id), lang))
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data:
        return json.loads(cache_data)
    else:
        url = "https://esi.evetech.net/latest/dogma/attributes/{}/?datasource=tranquility&language={}".format(attribute_id,lang)
        response = getSession().get(url)
        if response.status_code == 200:
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


class EvetechImage(Enum):
    alliances = ["alliances", "logo"]
    characters = ["characters", "portrait"]
    types_icon = ["types", "icon"]
    types_render = ["types", "render"]
    types_bpc = ["types", "bpc"]
    types_bp = ["types", "bp"]
    types_relict = ["types", "relict"]
    corporations = ["corporations", "logo"]


def esiImageEvetechNet(character_id: int, req_type, image_size=64):
    """Downloading the avatar for a player/character
       - https://docs.esi.evetech.net/docs/image_server.html
    Args:
        int id:ident to fined
        evetech_image type:type of image
        image_size: size of the image, 32, 64, 128, 256, 512, and 1024.

    Returns:
        bytearray: None if something gone wrong, else the png
    """

    avatar = None
    if character_id:
        url = "https://images.evetech.net/{type}/{id}/{info}?tenant=tranquility&size={size}".format(
            id=character_id, size=image_size, type=req_type[0], info=req_type[1])
        response = getSession().get(url)
        if response.status_code == 200:
            return response.content
        else:
            _logResponseError(response)
            response.raise_for_status()


def getTypesIcon(type_id: int, size_image=64) -> Optional[bytearray]:
    """Get icon from a given type_id or character_id

    Args:
        type_id:  id of type
        size_image: size of the image 32, 64 or 128

    Returns:
        bytearray: png image as bytearray

    """
    used_cache = Cache()
    img = used_cache.getImageFromIconCache(type_id)
    if img is None:
        url = "https://images.evetech.net/types/{id}/icon".format(id=type_id, size=size_image)
        response = getSession().get(url=url)
        if response.status_code == 200:
            used_cache.putImageToIconCache(type_id, response.content, secondUntilExpire(response))
            img = response.content
        else:
            _logResponseError(response)
            response.raise_for_status()
    if img:
        return bytearray(img)
    else:
        return None


def esiCharactersPortrait(char_name, image_size=64, use_cache=True):
    """Downloading the avatar for a player/character

    Args:
        char_name: name of the character
        image_size: size of the image, 32, 64, 128, 256, 512, and 1024.
        use_cache:
    Returns:
        bytearray: None if something gone wrong, else the png
    """
    cache = Cache()
    cached_data = cache.getImageFromAvatar(char_name) if use_cache else None
    if cached_data is None:
        avatar = None
        char_id = esiCharNameToId(char_name)
        if char_id:
            url = "https://images.evetech.net/characters/{id}/portrait/?tenant=tranquility&size={size}".format(
                id=char_id, size=image_size)
            response = getSession().get(url=url)
            if response.status_code == 200:
                avatar = response.content
                cache.putImageToAvatar(name=char_name, data=avatar, max_age=secondUntilExpire(response))
                return avatar
            else:
                _logResponseError(response)
                response.raise_for_status()
    else:
        return cached_data


def esiCharactersPublicInfo(char_name: str, use_cache: bool = True) -> object:
    """Downloading the public player/character info

    Args:
        char_name(str): name of the character
        use_cache(bool): use the cache
    Returns:
        dict: Dict holding the public data of the char, or None
    """
    cache = Cache()
    cache_key = u"_".join(("public_info_", char_name))
    cached_data = cache.getFromCache(cache_key) if use_cache else None
    if cached_data is None:
        char_id = esiCharNameToId(char_name, use_cache=use_cache)
        url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=char_id)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return json.loads(response.text)
        else:
            _logResponseError(response)
            response.raise_for_status()
    else:
        return json.loads(cached_data)


def checkPlayerName(char_name):
    """ Checking on esi for an exiting exact player name

        Args:
            char_name(str): name of the character

        Returns:
             int: 1 if exists, 0 if not and -1 if an error occurred
    """
    res_id = None
    if not char_name:
        return ERROR, res_id
    try:
        res_id = esiCharNameToId(char_name)
        if res_id:
            return EXISTS, res_id
        else:
            return NOT_EXISTS, res_id
    except Exception as e:
        logging.error("Exception on checkPlayerName: %s", e)
    return ERROR, res_id


def esiCharacters(char_id, use_outdated=False, use_cache=True):
    cache_key = u"_".join(("playerinfo_id_", str(char_id)))
    used_cache = Cache()
    cache_data = used_cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data is not None:
        return json.loads(cache_data)
    else:
        url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=int(char_id))
        response = getSession().get(url=url)
        if response.status_code == 200:
            used_cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiCheckCharacterToken(char_name: str) -> bool:
    return checkTokenTimeLine(getTokenOfChar(char_name)) is not None


def esiGetCharsOnlineStatus() -> list:
    """
        Fetch the connection status of all registered characters.
    Returns:
        List: [{"name": str,"online": bool, "system": str}]
    """
    result = list()
    for char in Cache().getAPICharNames():
        online = esiCharactersOnline(char)
        system = esiUniverseSystems(esiCharactersLocation(char))
        api_char = {
            "name": char,
            "online": online,
            "system": system
        }
        result.append(api_char)
    return result


def esiCharactersOnline(char_name: str) -> bool:
    """ Returns the online state of the char with name char_name.

    Args:
        char_name(str): The in game name of the char.

    Returns:
        bool:true if char is online, false otherwise .

    Raises:
        HTTPError:
    """
    token = checkTokenTimeLine(getTokenOfChar(char_name))
    if token:
        url = "https://esi.evetech.net/latest/characters/{}/online/?datasource=tranquility&token={}".format(
            esiCharNameToId(char_name), token.access_token)
        response = getSession().get(url=url)
        if response.status_code == 200:
            char_online = response.json()
            if "online" in char_online.keys():
                return char_online["online"]
            else:
                return False
        else:
            _logResponseError(response)
            response.raise_for_status()
    else:
        return False


def esiCharactersLocation(char_name: str) -> Optional[int]:
    """Gets the current solar system id of the char with id char_id, or None

    Args:
        char_name(str):The in game name of the character

    Returns:
        int: Current system_id or None

    Raises:
        HTTPError:
    """
    token = checkTokenTimeLine(getTokenOfChar(char_name))
    if token:
        url = "https://esi.evetech.net/latest/characters/{}/location/?datasource=tranquility&token={}".format(
            esiCharNameToId(char_name),
            token.access_token)
        response = getSession().get(url=url)
        if response.status_code == 200:
            char_location = response.json()
            if "solar_system_id" in char_location.keys():
                return char_location["solar_system_id"]
        else:
            _logResponseError(response)
            response.raise_for_status()
    return None


def esiCharactersCorporationHistory(char_id, use_outdated=True, use_cache=True):
    """ Returns a list with the ids if the corporation history of a charId
        returns a list of only the corp structs
        @param char_id id the char
        @param use_outdated also return outdated results from cache
        @param use_cache
    """
    cache_key = u"_".join(("corp_history_id_", str(char_id)))
    cache = Cache()
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data is not None:
        return json.loads(cache_data)
    else:
        char_id = int(char_id)
        url = "https://esi.evetech.net/latest/characters/{id}/corporationhistory/?datasource=tranquility".format(
            id=char_id)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def getCurrentCorpForCharId(char_id, use_outdated=True) -> Optional[int]:
    """ Returns the ID of the players current corporation.
    """
    info = esiCharacters(char_id, use_outdated)
    if info and "corporation_id" in info.keys():
        return info["corporation_id"]
    else:
        logging.error("Unable to get corporation_id of char id:{}".format(char_id))
        return None


def esiUniverseSystem_jumps(use_outdated=False, use_cache=True):
    """ Reads the information for all solarsystem from the EVE API cached 3600 s
        Reads a dict like:
            systemid: "jumps", "shipkills", "factionkills", "podkills"
    """
    data = {}
    system_data = {}
    cache = Cache()
    # first the data for the jumps
    cache_key = "jumpstatistic"
    jump_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    try:
        if jump_data is None:
            jump_data = {}
            url = "https://esi.evetech.net/latest/universe/system_jumps/?datasource=tranquility"
            response = getSession().get(url=url)
            if response.status_code != 200:
                _logResponseError(response)
                response.raise_for_status()
            resp = response.json()
            for row in resp:
                jump_data[int(row["system_id"])] = int(row["ship_jumps"])
            # todo check secondUntilExpire(response)
            cache.putIntoCache(cache_key, json.dumps(jump_data), max_age=secondUntilExpire(response))
        else:
            jump_data = json.loads(jump_data)

        cache_key = "systemstatistic"
        data_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
        if data_data is None:
            system_data = {}
            url = "https://esi.evetech.net/latest/universe/system_kills/?datasource=tranquility"
            response = getSession().get(url=url)
            if response.status_code != 200:
                _logResponseError(response)
                response.raise_for_status()
            resp = response.json()
            for row in resp:
                system_data[int(row["system_id"])] = {"ship": int(row["ship_kills"]),
                                                      "faction": int(row["npc_kills"]),
                                                      "pod": int(row["pod_kills"])}

            cache.putIntoCache(cache_key, json.dumps(system_data), max_age=secondUntilExpire(response))
        else:
            system_data = json.loads(data_data)
    except Exception as e:
        logging.error("Exception during getSystemStatistics: : %s", e)

    for i, v in jump_data.items():
        i = int(i)
        if i not in data:
            data[i] = {"shipkills": 0, "factionkills": 0, "podkills": 0}
        data[i]["jumps"] = v
    for i, v in system_data.items():
        i = int(i)
        if i not in data:
            data[i] = {"jumps": 0}
        data[i]["shipkills"] = v["ship"] if "ship" in v else 0
        data[i]["factionkills"] = v["faction"] if "faction" in v else 0
        data[i]["podkills"] = v["pod"] if "pod" in v else 0

    return data


class MyApiServer(http.server.BaseHTTPRequestHandler):
    """http server to get the redirected login message
    """
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>Spyglass API Registration</title></head>".encode("utf-8"))
        self.wfile.write("<body onload=\"closePage()\"><p>Close this page to complete registration.</p>".encode(
            "utf-8"))
        self.wfile.write("<script>function closePage(){self.close();}</script>".encode("utf-8"))
        self.wfile.write("</body></html>".encode("utf-8"))
        self.wfile.close()
        try:
            code = self.requestline.split(" ")[1]
            pos_code = code.find("code=")
            pos_state = code.find("&state=")
            self.server.api_code = code[pos_code + 5:pos_state]
            self.server.api_state = code[pos_state+6:]
            self.server.server_close()
        except Exception as e:
            logging.error("Exception during MyApiServer: %s", e)
            self.server.api_code = None


class APIServerThread(QThread):
    new_serve_aki_key = Signal(str)
    LIST_CHARS = list()
    WEB_SERVER_LOCK = threading.Lock()

    def __init__(self, params, browser=None):
        QThread.__init__(self)
        self.client_param = params
        self.queue = queue.Queue()
        self.active = True
        self.auth_code = None
        self.browser = browser
        self.webserver = None

    # todo: use https server here see: https://anvileight.com/blog/posts/simple-python-http-server/

    """
        openssl req -x509 -newkey rsa:2048 -keyout spyglass-key.pem -out spyglass-cert.pem -days 365
        openssl req -new -newkey rsa:4096 -x509 -sha256 -days 365 -nodes -out cert.crt -keyout private.key

        https://learn.microsoft.com/en-us/azure/application-gateway/self-signed-certificates
        
        openssl ecparam -out contoso.key -name prime256v1 -genkey
        openssl req -new -sha256 -key contoso.key -out contoso.csr
        openssl x509 -req -sha256 -days 365 -in contoso.csr -signkey contoso.key -out contoso.crt
        openssl ecparam -out fabrikam.key -name prime256v1 -genkey
        openssl req -new -sha256 -key fabrikam.key -out fabrikam.csr
        openssl x509 -req -in fabrikam.csr -CA  contoso.crt -CAkey contoso.key -CAcreateserial -out fabrikam.crt -days 365 -sha256
        openssl x509 -in fabrikam.crt -text -noout
        
    """
    def run(self):
        while self.active:
            try:
                with APIServerThread.WEB_SERVER_LOCK:
                    self.webserver = http.server.HTTPServer(("127.0.0.1", 8182), MyApiServer)
                    self.webserver.timeout = 240
                    self.webserver.api_code = None
                    self.webserver.close_connection = True
                self.webserver.handle_request()
                self.auth_code = self.webserver.api_code
                with APIServerThread.WEB_SERVER_LOCK:
                    self.webserver = None
                if self.auth_code is not None:
                    esiOauthToken(self.client_param, self.auth_code)
            except (Exception,) as e:
                logging.error("Error in APIServerThread.run: %s", e)

            self.browser = None
            self.active = False

    def createBrowserWindow(self, string_params, parent=None):
        """
            create the browser widget to login
        Args:
            string_params: param string to pass to web
            parent:None for system browser or a QObject with api_thread

        Returns:

        """

        if self.browser and parent:
            self.browser.destroyed.connect(self.quit)
            self.browser.load(QUrl("https://login.eveonline.com/v2/oauth/authorize?{}".format(string_params)))
            self.browser.resize(600, 800)
            self.browser.show()
        else:
            webbrowser.open_new("https://login.eveonline.com/v2/oauth/authorize?{}".format(string_params))

        logging.info("Awaiting registration during the next 120 seconds to be completed.")
        while self.isRunning():
            QtWidgets.QApplication.processEvents()

        if self.auth_code:
            logging.info("Registration completed.")
            return True
        else:
            logging.error("Registration not succeeded.")
            return False

    def quit(self):
        self.active = False
        if self.browser:
            self.browser.close()
        with APIServerThread.WEB_SERVER_LOCK:
            if self.webserver:
                getSession().get(url="http://127.0.0.1:8182/oauth-callback")
        QThread.quit(self)


class WebHostWidget(QWebEngineView):
    """
    notify the close event to terminate the thread
    """
    terminate_thread = Signal()

    def __init__(self, parent=None):
        super(WebHostWidget, self).__init__(parent)
        self.page().certificateError.connect(self.on_cert_error)

    def on_cert_error(self, e):
        print(f"cert error: {e.description()}")
        print(f"type: {e.type()}")
        print(f"overridable: {e.isOverridable()}")
        print(f"url: {e.url()}")
        for c in e.certificateChain():
            print(c.toText())
        e.acceptCertificate()

    def closeEvent(self, event):
        self.terminate_thread.emit()
        event.accept()


def oauthLoginEveOnline(client_param, parent=None):
    """ Queries the eve-online api key valid for one eve online account,
        using http://127.0.0.1:8182/oauth-callback as application defined
        callback from inside the webb browser
        params client_id, scope and state see esi-docs
    """
    used_hash = hashlib.sha256()
    used_hash.update(client_param["random"])
    digs = used_hash.digest()
    code_challenge = base64.urlsafe_b64encode(digs).decode().replace("=", "")
    params = {
        "response_type": "code",
        "redirect_uri": "http://127.0.0.1:8182/oauth-callback",
        "client_id": client_param["client_id"],
        "scope": client_param["scope"],
        "state": client_param["state"],
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    string_params = urllib.parse.urlencode(params)

    if parent:
        if hasattr(parent, 'apiThread') and parent.apiThread:
            parent.apiThread.quit()
    else:
        class Object(object):
            pass

        parent = Object()
        parent.apiThread = None

    web_view = WebHostWidget()
    parent.apiThread = APIServerThread(client_param, web_view)
    web_view.terminate_thread.connect(parent.apiThread.terminate)
    parent.apiThread.start()
    return parent.apiThread.createBrowserWindow(string_params, parent)


def esiOauthToken(client_param, auth_code: str, add_headers: dict = None) -> Optional[dict]:
    """ gets the access token from the application logging
        fills the cache wit valid login data
    """
    form_values = {
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
    response = getSession().post(
        url="https://login.eveonline.com/v2/oauth/token",
        data=form_values,
        headers=headers,
    )
    if response.status_code == 200:
        oauth_call = response.json()
        header = {
            "Authorization": "{} {}".format(oauth_call["token_type"], oauth_call["access_token"]),
        }
        oauth_result = getSession().get(url="https://login.eveonline.com/oauth/verify", headers=header)
        if response.status_code == 200:
            char_api_key_set = oauth_result.json()
            char_api_key_set.update(oauth_call)
            Cache().putAPIKey(char_api_key_set)
            return char_api_key_set["CharacterName"]
        else:
            _logResponseError(response)
            response.raise_for_status()
    else:
        _logResponseError(response)
        response.raise_for_status()
    return None


def openWithEveonline(parent=None):
    """perform an api key request and updates the cache on case of a positive response
        returns the selected username from the login
        see: https://developers.eveonline.com/applications/details/69202
    """
    client_param_set = {
        "client_id": APPLICATION_CLIENTS_ID,
        "scope": "esi-location.read_location.v1 esi-search.search_structures.v1 esi-universe.read_structures.v1 "
                 "esi-ui.write_waypoint.v1 esi-characters.read_standings.v1 esi-location.read_online.v1",
        "random": base64.urlsafe_b64encode(secrets.token_bytes(32)),
        "state": base64.urlsafe_b64encode(secrets.token_bytes(8))
    }
    return oauthLoginEveOnline(client_param_set, parent)


def getTokenOfChar(char_name) -> Optional[ApiKey]:
    """gets the api key for char_name, or id from the cache, Result is the last ApiKey, or None

    Args:
        char_name: name of the char
    """
    if char_name is None:
        return None
    char_data = Cache().getAPIKey(char_name)
    if char_data:
        return ApiKey(json.loads(char_data))
    else:
        if char_name not in APIServerThread.LIST_CHARS:
            logging.debug("The character '{}' is not registered with ESI.".format(char_name))
            APIServerThread.LIST_CHARS.append(char_name)
        return None


def refreshToken(params: Optional[ApiKey]) -> Optional[ApiKey]:
    """ refreshes the token using the previously acquired data structure from the cache
        if succeeded with result 200 the cache will be updated too
    """
    if params is None:
        return None
    if params.refresh_token is None:
        return None

    data = {
        "grant_type": "refresh_token",
        "refresh_token": params.refresh_token,
        "client_id": APPLICATION_CLIENTS_ID,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    response = getSession().post("https://login.eveonline.com/v2/oauth/token", data=data, headers=headers)
    if response.status_code == 200:
        ref_token = response.json()
        params.update(ref_token)

        cache = Cache()
        cache_api_key = cache.getAPIKey(params.CharacterName)
        if cache_api_key is None:
            return params
        char_api_key_set = json.loads(cache_api_key)
        char_api_key_set["ExpiresOn"] = \
            datetime.datetime.fromtimestamp(time.time() + params.expires_in,
                                            tz=datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        char_api_key_set["valid_until"] = \
            time.time() + params.expires_in
        char_api_key_set.update(ref_token)
        cache.putAPIKey(char_api_key_set)
        return getTokenOfChar(params.CharacterName)
    else:
        return getTokenOfChar(params.CharacterName)


# todo :  handle refresh of token if response is {"error":"token is expired","sso_status":200}
def checkTokenTimeLine(param: Optional[ApiKey]) -> Optional[ApiKey]:
    """
        double-check the api timestamp, if expired the parm set will be updated

    Args:
        param: ApiKey to check

    Returns:
        updated ApiKey or None
    """
    if param is None:
        return None
    if param.valid_until is not None and param.valid_until > time.time():
        return param
    else:
        return refreshToken(param)


def sendTokenRequest(form_values, add_headers=None):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "login.eveonline.com",
    }
    if add_headers:
        headers.update(add_headers)

    response = getSession().post(
        "https://login.eveonline.com/v2/oauth/token",
        data=form_values,
        headers=headers,
    )

    print("Request sent to URL {} with headers {} and form values: "
          "{}\n".format(response.url, headers, form_values))
    if response.status_code == 200:
        return response
    else:
        _logResponseError(response)
        response.raise_for_status()


def esiAutopilotWaypoint(char_name: str, system_id: int, beginning=True, clear_all=True):
    token = checkTokenTimeLine(getTokenOfChar(char_name))
    if token:
        route = {
            "add_to_beginning": beginning,
            "clear_other_waypoints": clear_all,
            "datasource": "tranquility",
            "destination_id": system_id,
            "token": token.access_token,
        }
        url = "https://esi.evetech.net/latest/ui/autopilot/waypoint/?{}".format(urllib.parse.urlencode(route))
        response = getSession().post(url=url)
        if response.status_code != 204:
            _logResponseError(response)
            response.raise_for_status()
        else:
            return True
    else:
        return False


def getRouteFromEveOnline(jumpgates, src, dst):
    """build rout respecting jump bridges
        returns the list of systems to travel to
    """
    route_elements = ""
    for elem in jumpgates:
        if route_elements != "":
            route_elements = route_elements + ","
        route_elements = route_elements + "{}|{}".format(elem[0], elem[1])

    url = "https://esi.evetech.net/v1/route/{}/{}/?connections={}".format(src, dst, route_elements)
    response = getSession().get(url=url)
    if response.status_code == 200:
        return response.json()
    else:
        _logResponseError(response)
        response.raise_for_status()


def esiIncursions(use_outdated=False, use_cache=True):
    """builds a list of incursion dicts cached 300 s
    """
    cache = Cache()
    cache_key = "incursions"
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data:
        return json.loads(cache_data)
    else:
        url = "https://esi.evetech.net/latest/incursions/?datasource=tranquility"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()
    return []


def getIncursionSystemsIds(use_outdated=False, use_cache=True):
    inc_systems = list()
    incursion_list = esiIncursions(use_outdated=use_outdated, use_cache=use_cache)
    for constellations in incursion_list:
        for sys in constellations["infested_solar_systems"]:
            inc_systems.append(sys)
    return inc_systems


def esiSovereigntyCampaigns(use_outdated=False, use_cache=True):
    """builds a list of reinforced campaigns for IHUB  and TCU dicts cached 60 s
    """
    cache = Cache()
    cache_key = "sovereignty_campaigns"
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data:
        return json.loads(cache_data)
    else:
        url = "https://esi.evetech.net/latest/sovereignty/campaigns/?datasource=tranquility"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))  # 5 seconds from esi
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiSovereigntyStructures(use_outdated=False, use_cache=True):
    """
    Shows sovereignty data for structures.

    Args:
        use_outdated:
        use_cache:
    Returns:

    """
    cache = Cache()
    cache_key = "sovereignty_structures"
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data:
        return json.loads(cache_data)
    else:
        url = "https://esi.evetech.net/latest/sovereignty/structures/?datasource=tranquility"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiSovereigntyMap(use_outdated=False, use_cache=True):
    """
    Shows sovereignty information for solar systems

    Args:
        use_outdated:
        use_cache:
    Returns:

    """
    cache = Cache()
    cache_key = "sovereignty_map"
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data is not None:
        return json.loads(cache_data)
    else:
        url = "https://esi.evetech.net/latest/sovereignty/map/?datasource=tranquility"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def getCampaignsSystemsIds(use_outdated=False):
    """builds a list of system ids being part of campaigns for hubs and tcus dicts cached 60s
    """
    curr_campaigns = list()
    for system in esiSovereigntyCampaigns(use_outdated):
        curr_campaigns.append(system["solar_system_id"])
    return curr_campaigns


def getCampaignsStructureIds(use_outdated=False):
    """builds a list of system ids being part of campaigns for hubs and tcus dicts cached 60s
    """
    curr_campaigns = list()
    for system in esiSovereigntyCampaigns(use_outdated):
        curr_campaigns.append(system["structure_id"])
    return curr_campaigns


def getAllStructures(typeid=None):
    url = "https://esi.evetech.net/latest/universe/structures/?datasource=tranquility"
    response = getSession().get(url=url)
    if response.status_code == 200:
        structs_found = response.json()
        if typeid is None:
            return structs_found
        types = list()
        for structure in structs_found:
            if "structure_type_id" in structure.keys():
                if structure["structure_type_id"] == typeid:
                    types.append(structure)
        return types
    else:
        _logResponseError(response)
        response.raise_for_status()


def esiUniverseStructure(esi_char_name: str, structure_id: int, use_outdated=False, use_cache=False):
    """"Calls https://esi.evetech.net/ui/#/Universe/get_universe_structures
    """
    res_value = None
    if esi_char_name is None:
        logging.error("esiUniverseStructure needs the eve-online api account.")
        return res_value
    cache_key = "_".join(("structure", "id", str(structure_id)))
    cache = Cache()
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data is not None:
        res_value = json.loads(cache_data)
        res_value["structure_id"] = structure_id
    else:
        token = checkTokenTimeLine(getTokenOfChar(esi_char_name))
        if token:
            url = "https://esi.evetech.net/latest/universe/structures/{}/?datasource=tranquility&token={}".format(
                structure_id, token.access_token)
            response = getSession().get(url=url)
            if response.status_code == 200:
                cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
                res_value = response.json()
                res_value["structure_id"] = structure_id
            else:
                _logResponseError(response)
                response.raise_for_status()

    return res_value


def esiCorporationsStructures(esi_char_name: str, corporations_id: int, use_outdated=False, use_cache=True):
    """"Calls https://esi.evetech.net/ui/#/Universe/get_universe_structures
    """
    res_value = None
    if esi_char_name is None:
        logging.error("esiUniverseStructure needs the eve-online api account.")
        return res_value
    cache_key = "_".join(("corporations", "structures", "id", str(corporations_id)))
    cache = Cache()
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data is not None:
        res_value = json.loads(cache_data)
    else:
        token = checkTokenTimeLine(getTokenOfChar(esi_char_name))
        if token:
            url = "https://esi.evetech.net/latest/corporations/{}/structures/?datasource=tranquility&token={}"\
                .format(corporations_id, token.access_token)
            response = getSession().get(url=url)
            if response.status_code == 200:
                cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
                res_value = response.json()
            else:
                _logResponseError(response)
                response.raise_for_status()
    return res_value


def esiLatestSovereigntyMap(use_outdated=False, use_cache=True):
    """builds a list of reinforced campaigns for hubs and tcus dicts cached 60s
       https://esi.evetech.net/ui/?version=latest#/Sovereignty/get_sovereignty_map
    """
    cache = Cache()
    cache_key = "sovereignty"
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data is not None:
        campaigns_list = json.loads(cache_data)
    else:
        url = "https://esi.evetech.net/latest/sovereignty/map/?datasource=tranquility"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def getPlayerSovereignty(use_outdated=False, use_cache=True, show_npc=True, callback=None):
    seq = ""

    def update_callback(seq_in):
        if callback:
            seq_in = seq_in + "."
            callback("Fetch player sovereignty by ESI {}".format(seq_in))
            if len(seq_in) > 20:
                seq_in = ""
        return seq_in

    cache_key = "player_sovereignty"
    cache = Cache()
    cache_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cache_data is not None:
        return json.loads(cache_data)
    else:
        player_sov = dict()
        npc_sov = dict()
        set_of_all_factions = set()
        for sov in esiLatestSovereigntyMap(use_outdated, use_cache):
            if len(sov) > 2:
                player_sov[str(sov["system_id"])] = sov
            elif show_npc and len(sov) > 1:
                set_of_all_factions.add(sov["faction_id"])
                npc_sov[str(sov["system_id"])] = sov

        alliance_ids = set([player_sov[itm]["alliance_id"]
                            for itm in player_sov if "alliance_id" in player_sov[itm].keys()])
        for alliance_id in alliance_ids:
            esiAlliances(alliance_id)
        for sov in player_sov.values():
            if "alliance_id" in sov.keys():
                alli_id = sov["alliance_id"]
                sov["ticker"] = esiAlliances(alli_id)["ticker"]
            seq = update_callback(seq)

        if show_npc:
            npc_list = esiUniverseNames(set_of_all_factions)
            for sov in npc_sov.values():
                if "faction_id" in sov.keys():
                    sov["ticker"] = Universe.npcFactionNames(sov["faction_id"], npc_list)
                seq = update_callback(seq)
            player_sov.update(npc_sov)
        cache.putIntoCache(cache_key, json.dumps(player_sov), 3600)
        return player_sov


class JumpBridge(object):
    def __init__(self, name: str, structure_id: int, system_id: int, owner_id: int):
        tok = name.split(" ")
        self.src_system_name = tok[0]
        self.dst_system_name = tok[2]
        self.name = name
        self.structureId = structure_id
        self.systemId = system_id
        self.ownerId = owner_id
        self.paired = False
        self.links = 0


def sanityCheckGates(gates):
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


def countCheckGates(gates):
    for gate in gates:
        for elem in gates:
            if (gate.src_system_name == elem.src_system_name) or (gate.src_system_name == elem.dst_system_name):
                gate.links = gate.links+1


class Category(Enum):
    agent = "agent"
    alliance = "alliance"
    character = "character"
    constellation = "constellation"
    corporation = "corporation"
    faction = "faction"
    inventory_type = "inventory_type"
    region = "region"
    solar_system = "solar_system"
    station = "station"
    structure = "structure"


def esiSearch(esi_char_name: str, search_text, search_category: Category, search_strict=False):
    """ updates all jump bridge data via api searching for names which have a substring  %20%C2%BB%20 means " >> "
    """
    if esi_char_name is None:
        logging.error("esiSearch needs the eve-online api account.")
        return {}
    token = checkTokenTimeLine(getTokenOfChar(esi_char_name))
    if token is None:
        logging.error("esiSearch needs the eve-online api account.")
        return {}
    search_strict = "true" if search_strict else "false"
    url = "https://esi.evetech.net/v3/characters/{character_id}/search/?datasource=tranquility"\
          "&categories={cat}&strict={sstr}&search={sys}&token={tok}".format(
            character_id=token.CharacterID, tok=token.access_token,
            sys=search_text, cat=search_category, sstr=search_strict)
    response = getSession().get(url=url)
    if response.status_code == 200:
        return response.json()
    else:
        _logResponseError(response)
        response.raise_for_status()


def getAllJumpGates(name_char: str, system_name_src="", system_name_dst="",
                    callback=None, use_outdated=False) -> Optional[list]:
    """ updates all jump bridge data via api searching for names which have a substring  %20%C2%BB%20 means " >> "
    """
    if name_char is None:
        logging.error("getAllJumpGates needs the eve-online api account.")
        return None
    token = checkTokenTimeLine(getTokenOfChar(name_char))
    if token is None:
        logging.error("getAllJumpGates needs the eve-online api account.")
        return None

    url = "https://esi.evetech.net/v3/characters/{id}/search/?"\
          "datasource=tranquility&categories=structure&search={src}%20%C2%BB%20{dst}&token={tok}".format(
                id=token.CharacterID,
                tok=token.access_token,
                src=system_name_src,
                dst=system_name_dst)
    response = getSession().get(url=url)
    if response.status_code != 200:
        logging.error(response.reason)
        return None
    structs = response.json()
    gates = list()
    processed = list()
    if token and len(structs):
        process = 0
        if callback and not callback(len(structs["structure"]), process):
            return gates
        for id_structure in structs["structure"]:
            process = process + 1
            if callback and not callback(len(structs["structure"]), process):
                break
            if id_structure in processed:
                continue
            json_src = esiUniverseStructure(
                esi_char_name=name_char, structure_id=id_structure, use_outdated=use_outdated)
            if json_src is None:
                continue
            jump_bridge_text = parse.parse("{src} » {dst} - {info}", json_src["name"])
            structure = esiSearch(
                esi_char_name=name_char,
                search_text="{} » {}".format(jump_bridge_text["src"], jump_bridge_text["dst"]),
                search_category=Category.structure)

            if "structure" not in structure.keys():
                Cache().clearJumpGate(jump_bridge_text["src"])
                Cache().clearJumpGate(jump_bridge_text["dst"])
                Cache().putJumpGate(
                    src=jump_bridge_text.named["src"],
                    dst=jump_bridge_text.named["dst"],
                    src_id=None,
                    dst_id=None,
                    json_src=None,
                    json_dst=None,
                    used=0
                )
                continue
            cnt_structures = len(structure["structure"])
            if cnt_structures < 2:
                Cache().clearJumpGate(jump_bridge_text["src"])
                Cache().clearJumpGate(jump_bridge_text["dst"])
                continue

            for structure_id in structure["structure"]:
                processed.append(structure_id)

            json_src = esiUniverseStructure(
                esi_char_name=name_char,
                structure_id=structure["structure"][0])
            json_dst = esiUniverseStructure(
                esi_char_name=name_char,
                structure_id=structure["structure"][cnt_structures-1])

            Cache().putJumpGate(
                src=jump_bridge_text.named["src"],
                dst=jump_bridge_text.named["dst"],
                src_id=structure["structure"][0],
                dst_id=structure["structure"][cnt_structures-1],
                json_src=json_src,
                json_dst=json_dst,
                used=cnt_structures
            )
            if json_dst and json_dst:
                gates.append(
                    JumpBridge(name=json_src["name"], system_id=json_src["solar_system_id"],
                               structure_id=structure["structure"][0], owner_id=json_src["owner_id"]))
                gates.append(
                    JumpBridge(name=json_dst["name"], system_id=json_dst["solar_system_id"],
                               structure_id=structure["structure"][cnt_structures - 1], owner_id=json_dst["owner_id"]))
            process = process + 1

    countCheckGates(gates)
    return gates


def writeGatesToFile(gates, filename="jb.txt"):
    gates_list = list()
    with open(filename, "w")as gf:
        for gate in gates:
            s_t_d = "{} » {}".format(gate.src_system_name, gate.dst_system_name)
            d_t_s = "{} » {}".format(gate.dst_system_name, gate.src_system_name)
            if s_t_d not in gates_list and d_t_s not in gates_list:
                gf.write("{} {} {} {} ({} {})\n".format(
                    s_t_d, gate.system_id, gate.structureId, gate.ownerId, gate.links, gate.paired))
                gates_list.append(s_t_d)
        gf.close()


def esiUniverseStargates(stargate_id, use_outdated=False, use_cache=True):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "systems", str(stargate_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/stargates/{}/?datasource=tranquility&language=en".format(
            stargate_id)
        response = getSession().get(url=url)
        if response.status_code != 200:
            _logResponseError(response)
            response.raise_for_status()
        else:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()


def esiUniverseStations(station_id, use_outdated=False, use_cache=True) -> Optional[dict]:
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "stations", str(station_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/stations/{}/?datasource=tranquility&language=en".format(
            station_id)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseSystems(system_id, use_outdated=False, lang="en", use_cache=True) -> Optional[dict]:
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "systems", str(system_id), lang))
    cache = Cache()
    cached_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_data:
        return json.loads(cached_data)
    else:
        url = "https://esi.evetech.net/dev/universe/systems/{}/?datasource=tranquility&language={}".format(
            system_id, lang)
        ses = getSession()
        response = ses.get(url=url)
        if response.status_code == 200:
            response_json = response.json()
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response_json
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseAllSystems(use_outdated=False, use_cache=True):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "all", "systems"))
    cache = Cache()
    cached_data = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_data:
        return json.loads(cached_data)
    else:
        url = "https://esi.evetech.net/latest/universe/systems/?datasource=tranquility&language=en"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiAlliances(alliance_id, use_outdated=True, use_cache=True):
    """gets the alliance from the alliance id
    """
    cache_key = "_".join(("alliance", str(alliance_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/alliances/{}/?datasource=tranquility".format(alliance_id)
        response = getSession().get(url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()
        return {"ticker": "-"}


def esiUniverseRegions(region_id: int, use_outdated=False, use_cache=True, lang="en"):
    cache_key = "_".join(("universe", "regions", str(region_id), lang))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/regions/{}?datasource=tranquility&language={}".format(region_id, lang)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseGetAllRegions(use_outdated=False, use_cache=True) -> Optional[set]:
    """ Uses the EVE API to get the list of all region ids

    Returns:
             list : list of the ids of all regions
    """
    cache = Cache()
    all_systems = cache.getFromCache("universe_all_regions", use_outdated) if use_cache else None
    if all_systems is not None:
        return json.loads(all_systems)
    else:
        url = "https://esi.evetech.net/latest/universe/regions/?datasource=tranquility"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache("universe_all_regions", value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseConstellations(constellation_id: int, use_outdated=False, use_cache=True, lang="en"):
    cache_key = "_".join(("universe", "constellations", str(constellation_id), lang))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/constellations/{}/?datasource=tranquility&language={}".format(
            constellation_id, lang)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseAllConstellations(use_outdated=False, use_cache=True):
    cache_key = "universe_all_constellations"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/constellations/?datasource=tranquility&language=en"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseAllCategories(use_outdated=False, use_cache=True):
    """
    Get information of an item category


    Args:
        use_outdated:

    Returns:

    """
    cache_key = "universe_all_categories"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/categories/?datasource=tranquility&language=en"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseCategories(categorie_id: int, use_outdated=False, use_cache=True):
    """
    Get information of an item category


    Args:
        categorie_id:

        use_outdated:

    Returns:

    """
    cache_key = "universe_categories_{}".format(categorie_id)
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/categories/{}/?datasource=tranquility&language=en".format(
            categorie_id)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseAllGroups(categorie_id: int, use_outdated=False, use_cache=True):
    """
    Get information of an item category
    Args:
        categorie_id: categories
        use_outdated:
        use_cache:

    Returns:

    """
    cache_key = "universe_groups"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/groups/?datasource=tranquility&language=en"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseGroups(group_id: int, use_outdated=False, use_cache=True):
    """
    Get information of an item category
    Args:
        group_id:
        use_outdated:
        use_cache:
    Returns:

    """
    cache_key = "universe_group_{}".format(group_id)
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/groups/{}/?datasource=tranquility&language=en".format(group_id)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseAllTypes(types_id: int, use_outdated=False, use_cache=True):
    """
    Get information of an item category


    Args:
        types_id:
        use_outdated:
        use_cache:

    Returns:

    """
    cache_key = "universe_types"
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/types/?datasource=tranquility&language=en"
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiUniverseTypes(types_id: int, use_outdated=False, use_cache=True):
    """
    Get information of an item category


    Args:
        types_id:
        use_outdated:
        use_cache:

    Returns:

    """
    cache_key = "universe_types_{}".format(types_id)
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_id is not None:
        return json.loads(cached_id)
    else:
        url = "https://esi.evetech.net/latest/universe/types/{}/?datasource=tranquility&language=en".format(types_id)
        response = getSession().get(url=url)
        if response.status_code == 200:
            cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
            return response.json()
        else:
            _logResponseError(response)
            response.raise_for_status()


def esiCharactersStanding(char_name: str, use_outdated=False, use_cache=True):
    """
    Get information of characters standings


    Args:
        char_name
        use_outdated:
        use_cache:

    Returns:
        list:
    """
    cache_key = "characters_{}_standings".format(char_name)
    cache = Cache()
    cached_standing = cache.getFromCache(cache_key, use_outdated) if use_cache else None
    if cached_standing is not None:
        return json.loads(cached_standing)
    else:
        token = checkTokenTimeLine(getTokenOfChar(char_name))
        if token:
            url = "https://esi.evetech.net/latest/characters/{}/standings/?datasource=tranquility&token={}".format(
                esiCharNameToId(char_name), token.access_token)
            response = getSession().get(url=url)
            if response.status_code == 200:
                cache.putIntoCache(cache_key, value=response.text, max_age=secondUntilExpire(response))
                return json.loads(response.text)
            else:
                _logResponseError(response)
                response.raise_for_status()
    return list()


def hasAnsiblex(sys) -> bool:
    return False


def applyRouteToEveOnline(name_char, jump_list):
    if name_char is None:
        logging.error("applyRouteToEveOnline needs the eve-online api account.")
        return None
    for id_system in jump_list:
        if hasAnsiblex(id_system):
            pass
        else:
            esiAutopilotWaypoint(name_char, id_system, beginning=False, clear_all=False)


def checkSpyglassVersionUpdate(current_version=VERSION, force_check=False):
    """check GitHub for a new latest release
    """
    checked = Cache().getFromCache("version_check")
    if force_check or checked is None:
        url = "https://api.github.com/repos/jkey-67/spyglass/releases"
        response = getSession().get(url=url)
        if response.status_code != 200:
            _logResponseError(response)
            return [False, "Error %i : '%s' url: %s", response.status_code, response.reason, response.url]
        page_json_found = response.json()
        if len(page_json_found) > 0 and "tag_name" in page_json_found[0].keys():
            new_version = page_json_found[0]["tag_name"][1:]
        else:
            return [False, "Unable to read version from github."]
        Cache().putIntoCache("version_check", new_version, 60 * 60)
        if version.parse(new_version) > version.parse(current_version):
            return [True,
                    "An newer Spyglass Version {} is available, you are currently running Version {}.".format(
                        new_version, current_version)]
        else:
            return [False,
                    "You are running the actual Spyglass Version {}.".format(current_version)]
    else:
        return [False,
                "Pending version check, current version is {}.".format(checked)]


def ESAPIHealth():
    """
        Report the process health to the Azure App Service environment.
    Returns:
        Dict
    """
    req = "https://api.eve-scout.com/v2/health"
    response = getSession().get(req, timeout=1)
    if response.status_code == 200:
        return response.json()
    else:
        _logResponseError(response)
        return dict()


def ESAPIListPublicObservationsRecords(use_cache=True):
    """
        List observation records for all objects eve scout tracks
    Attributes:
        use_cache:
    Returns:
        list of dicts
    """
    used_cache = Cache()
    cache_key = "Eve_Scout_Observations_Records"
    observations_records = used_cache.getFromCache(cache_key) if use_cache else None
    if observations_records is None:
        req = "https://api.eve-scout.com/v2/public/observations"
        response = getSession().get(req)
        if response.status_code == 200:
            used_cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
            return response.json()
        else:
            response.raise_for_status()
            return []
    else:
        return json.loads(observations_records)


def ESAPIListPublicSignatures(use_cache=True):
    """
        List all public resources in the signatures collection. A signature is considered "public" if it has been fully
        scanned and has not expired or been deleted.

    NOTES:
        The EOL status of a signature can be determined by its expires_at property. If this drops below 4 hours,
        the wormhole is getting close to its end of life.
        To locate the entrance and exit of the wormhole, wh_exits_outward can be used. When set to true, the wormhole
        type is on the hub's side (Thera or Turnur) and K162 can be found on the outside.
    See:
        https://api.eve-scout.com/ui/

    Arguments:
        use_cache:

    Returns:
        list of dicts
    """
    used_cache = Cache()
    cache_key = "Eve_Scout_Public_Signatures"
    list_public_signatures = used_cache.getFromCache(cache_key) if use_cache else None
    if list_public_signatures is None:
        req = "https://api.eve-scout.com/v2/public/signatures"
        response = getSession().get(req)
        if response.status_code == 200:
            used_cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
            return response.json()
        else:
            return []
    return json.loads(list_public_signatures)


def ESAPIListWormholeTypes(use_cache=True):
    """
        List all wormhole types filtered by the specified parameters. If more than one filter at a time is provided,
        they will be applied one after the other (AND).
    See:
        https://api.eve-scout.com/ui/

    Args:
        use_cache:
    Returns:
        list of dicts
    """
    used_cache = Cache()
    cache_key = "Eve_List_Wormhole_Types"
    list_wormhole_types = used_cache.getFromCache(cache_key) if use_cache else None
    if list_wormhole_types is None:
        req = "https://api.eve-scout.com/v2/public/wormholetypes"

        response = getSession().get(req)
        if response.status_code == 200:
            used_cache.putIntoCache(cache_key, response.text, secondUntilExpire(response))
            return response.json()
        else:
            return None
    else:
        return json.loads(list_wormhole_types)


def ESAPIListSystems(query: str, limit=None, space="k-space"):
    """
        List all systems filtered by the specified parameters
    Args:
        query: The search query to match against the beginning of the name.
        limit: Limit the number of returned results to this number of elements. Must be an integer greater than 0.
        space: Allowed: k-space ┃ j-space
    See:
        https://api.eve-scout.com/ui/

    Returns:
        list of dicts
    """
    req = "https://api.eve-scout.com/v2/public/systems?query={}&space={}".format(query, space)
    if limit:
        req = req + "&limit={}".format(limit)
    response = getSession().get(req)
    if response.status_code == 200:
        return response.json()
    else:
        return []


def ESAPIRouteToHighSec(system_name: str):
    """
        Calculate up to five routes to the closest high-sec systems from the provided system. The routing algorithm
        removes all routes which have overlapping routes, e.g. if e.g. in route A->B->C systems B and C would be
        high-sec systems, A->B would be returned, while A->B->C would be omitted.
    See:
        https://api.eve-scout.com/ui/
    Args:
        system_name:

    Returns:

    """
    req = "https://api.eve-scout.com/v2/public/routes/highsec?from={}".format(system_name)
    response = getSession().get(req)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def checkTheraConnections(thera_connections, system_name=None, fetch_jump_route=True):
    """
        Prepares the distans fields based on the given system name
    Args:
        thera_connections:
        system_name:
        fetch_jump_route:
    Remarks:
        call this function not from the gui thread.
    Returns:
        dict: thera connections holding patched data
    """
    if system_name and len(thera_connections):
        src_id = Universe.systemIdByName(system_name)
        for thera_item in thera_connections:
            dst_id = thera_item["in_system_id"]
            if 31000920 != src_id and 31000920 != dst_id:
                if fetch_jump_route:
                    cons = len(RoutPlanner.findRoute(src_id=src_id, dst_id=dst_id, use_ansi=True, use_thera=False).route)
                    thera_item["jumps"] = cons-1 if cons > 0 else 0
    return thera_connections


def getSpyglassUpdateLink(ver=VERSION):
    req = "https://api.github.com/repos/jkey-67/spyglass/releases"
    response = requests.get(req)
    if response.status_code != 200:
        return [False, "Error %i : '%s' url: %s", response.status_code, response.reason, response.url]
    page_json_found = response.json()
    if len(page_json_found) > 0 and "assets" in page_json_found[0].keys():
        return page_json_found[0]["assets"][0]["browser_download_url"]
    else:
        return None


def convertRegionNameForDotlan(name: str) -> str:
    """
        Converts a (system)name to the format that dotlan uses
    """
    converted = []
    next_upper = False

    for index, char in enumerate(name):
        if index == 0:
            converted.append(char.upper())
        else:
            if char in (u" ", u"_"):
                char = u"_"
                next_upper = True
            else:
                if next_upper:
                    char = char.upper()
                else:
                    char = char.lower()
                next_upper = False
            converted.append(char)
    return u"".join(converted)


def getSvgFromDotlan(region: str, dark: bool = True) -> str:
    """
    Gets the svg map from dotlan

    Args:
        region(str): name or the region space will be converted to _ url is lower
        dark(bool): if dark is true, the darkregion.dark.svg image svg is loaded else wise the normal
    Returns:
        The loaded svg map as text.
    """
    if dark:
        url = u"https://evemaps.dotlan.net/svg/{0}.dark.svg".format(convertRegionNameForDotlan(region))
    else:
        url = u"https://evemaps.dotlan.net/svg/{0}.svg".format(convertRegionNameForDotlan(region))
    response = getSession().get(url)
    if response.status_code == 200:
        return response.text
    else:
        logging.info("Unable to get svg from dotlan : {}".format(url))
        return '<?xml version="1.0"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg/>'
        #  return "<b>region not found</b>"


def esiGetFactions():
    """
    Get information of ALL FACTIONS
    Returns:

    """
    url = "https://esi.evetech.net/latest/universe/factions/?datasource=tranquility&language=en"
    response = getSession().get(url=url)
    if response.status_code == 200:
        return response.json()
    else:
        _logResponseError(response)
        response.raise_for_status()


def dumpSpyglassDownloadStats():
    req = "https://api.github.com/repos/jkey-67/spyglass/releases"
    response = requests.get(req)
    if response.status_code == 200:
        page_json_found = response.json()
        for item in page_json_found:
            if "assets" in item.keys():
                for asset in item["assets"]:
                    cnt = asset["download_count"]
                    name = asset["browser_download_url"]
                    print("Statistic of {} download count {}".format(name, cnt))
        return page_json_found
    else:
        _logResponseError(response)
        response.raise_for_status()


def generate_universe_constellation_names(use_outdated=True):
    esiUniverseAllSystems()
    print("Constellation generation started ...")
    constellation_id_by_name = dict()
    data = esiUniverseAllConstellations()
    count = len(data)
    pos = 1
    for constellation_id in esiUniverseAllConstellations():
        print("Constellation id {} {}/{} {:.1f}%".format(constellation_id, pos, count, (pos / count * 100)))
        for lang in ("en", "en-us", "de", "fr", "ja", "ru", "zh", "ko", "es"):
            res = esiUniverseConstellations(constellation_id, lang=lang, use_outdated=use_outdated)
            constellation_id_by_name[res["name"]] = res["constellation_id"]
        pos += 1

    print("Constellation generation done.")
    with open("universe/constellationnames.py.new", "w", encoding="utf-8") as out_file:
        out_file.write('# this file is auto generated, do not edit.\n')
        out_file.write('CONNSTELLATION_IDS_BY_NAME = {\n')
        data_out = set(constellation_id_by_name.items())
        last = len(data_out)
        for key, data in set(constellation_id_by_name.items()):
            if last == 1:
                out_file.write('   u"{}": {}\n'.format(key, data))
            else:
                out_file.write('   u"{}": {},\n'.format(key, data))
            last -= 1
        out_file.write('}\n')

    if os.path.exists("universe/constellationnames.py.new"):
        if os.path.exists("universe/constellationnames.py"):
            os.remove("universe/constellationnames.py")
        os.renames("universe/constellationnames.py.new", "universe/constellationnames.py")


def is_null_sec_system_name(name: str):
    """
        Roughly check if name match null sec criteria
    Args:
        name:

    Returns:
        true if 6 chars and all upper

    """
    if len(name) != 6 or not name.isupper():
        return False
    else:
        return True


def generate_universe_system_names(use_outdated=True):
    languages = ("en", "en-us", "de", "fr", "ja", "ru", "zh", "ko", "es")
    systems = esiUniverseAllSystems(use_cache=False)

    systems_cnt = []
    systems_id_by_name = {}
    pos = 1
    count = (len(systems) + 1) * len(languages)
    with open("universe/systemnames.json.new", "w", encoding="utf-8")as out_file:
        out_file.write(u'{\n')
        for system_id in systems:
            for lang in languages:
                pos = pos + 1
                if system_id in systems_cnt:
                    continue
                retry = 1
                res = {}
                while retry < 4:
                    res = esiUniverseSystems(system_id, lang=lang, use_cache=True, use_outdated=use_outdated)
                    if res and "name" in res and "system_id" in res:
                        if retry > 1 :
                            print("System id {} '{}' '{}' {}/{} {:.1f}%".format(
                                system_id, lang, res["name"], pos, count, (pos / count * 100)))
                        systems_id_by_name[res["name"]] = res["system_id"]
                        if is_null_sec_system_name(res["name"]):
                            systems_cnt.append(system_id)
                        break
                    else:
                        print("Retry creating system name for id: {} lang: '{}' retry : #{}.".format(
                            system_id, lang, retry))
                        retry = retry + 1

        print("Generation of systemnames.json done.")

        data_write = set(systems_id_by_name.items())
        last = len(data_write)
        for key, data in data_write:
            if last == 1:
                out_file.write(u'   "{}": {}\n'.format(key, json.dumps(data)))
            else:
                out_file.write(u'   "{}": {},\n'.format(key, json.dumps(data)))
            last -= 1
        systems_id_by_name.clear()
        out_file.flush()

        out_file.write(u'}\n\n')

    if os.path.exists("universe/systemnames.json.new"):
        if os.path.exists("universe/systemnames.json"):
            os.remove("universe/systemnames.json")
        os.renames("universe/systemnames.json.new", "universe/systemnames.json")


def generate_universe_region_names(use_outdated=True):
    print("Region generation started ...")
    pos = 1
    regions = esiUniverseNames(esiUniverseGetAllRegions(), use_outdated=use_outdated)
    count = len(regions)
    region_id_by_name = dict()
    for region_id in regions:
        print("Region id {} {}/{} {:.1f}%".format(region_id, pos, count, (pos / count * 100)))
        for lang in ("en", "en-us", "de", "fr", "ja", "ru", "ko", "es", "zh"):
            res = esiUniverseRegions(region_id, lang=lang, use_outdated=use_outdated)
            if res and "name" in res and "region_id" in res:
                region_id_by_name[res["name"]] = res["region_id"]
            else:
                continue
        pos += 1

    with open("universe/regionnames.py.new", "w", encoding="UTF-8") as out_file:
        out_file.write('# this file is auto generated, do not edit.\n')
        out_file.write('REGION_IDS_BY_NAME = {\n')
        rgn_out = set(region_id_by_name.items())
        last = len(rgn_out)
        for key, data in rgn_out:
            if last == 1:
                out_file.write('   "{}": {}\n'.format(key, data))
            else:
                out_file.write('   "{}": {},\n'.format(key, data))
            last -= 1
        out_file.flush()

        out_file.write('}\n')
        print("Region generation done.")

    if os.path.exists("universe/regionnames.py.new"):
        if os.path.exists("universe/regionnames.py"):
            os.remove("universe/regionnames.py")
        os.renames("universe/regionnames.py.new","universe/regionnames.py")


def esiPing() -> bool:
    """
        Simple 'ping' and check response to be 'ok'
    Returns:

    """
    req = "https://esi.evetech.net/ping"
    response = getSession().get(req)
    if response.status_code == 200:
        return response.text == "ok"
    else:
        return False



def esiStatusJson():
    """
        Fetch the status of the endpoints
    Returns:
        dict() : holding the data
    """
    req = "https://esi.evetech.net/status.json?version=latest"
    response = getSession().get(req)
    if response.status_code != 200:
        return dict()
    else:
        return response.json()

